import asyncio
import random
from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3, Web3
from typing import Dict

from src.utils.config import Config
from src.utils.constants import RPC_URL, EXPLORER_URL
from .constants import DEPLOY_CONTRACT_BYTECODE


class Owlto:
    def __init__(
        self,
        account_index: int,
        proxy: str,
        private_key: str,
        config: Config,
        session: AsyncClient,
    ):
        self.account_index = account_index
        self.proxy = proxy
        self.private_key = private_key
        self.config = config
        self.session = session

        self.account: Account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))

    async def get_gas_params(self) -> Dict[str, int]:
        """Get current gas parameters from the network."""
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee

        # Calculate maxFeePerGas (base fee + priority fee)
        max_fee = base_fee + max_priority_fee

        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add some buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            # 添加10%的estimated gas用于安全
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    async def deploy_contract(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                logger.info(f"[{self.account_index}] Deploying Owlto contract...")

                gas_params = await self.get_gas_params()

                # 创建用于估算gas的基础交易
                transaction = {
                    "from": self.account.address,
                    "data": DEPLOY_CONTRACT_BYTECODE,  # 使用正确的常量名称
                    "chainId": 10143,
                    "type": 2,
                    "value": 0,  # 不发送MON进行部署
                }

                # 估算gas
                estimated_gas = await self.estimate_gas(transaction)
                logger.info(f"[{self.account_index}] Estimated gas: {estimated_gas}")

                # 添加其他交易参数
                transaction.update(
                    {
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address,
                            "latest",
                        ),
                        "gas": estimated_gas,
                        **gas_params,
                    }
                )

                signed_txn = self.web3.eth.account.sign_transaction(
                    transaction, self.private_key
                )
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # 等待交易确认
                logger.info(
                    f"[{self.account_index}] Waiting for contract deployment confirmation..."
                )
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                logger.success(
                    f"[{self.account_index}] Successfully deployed Owlto contract at {receipt['contractAddress']}. TX: {EXPLORER_URL}{tx_hash.hex()}"
                )
                return True

            except Exception as e:
                random_pause = random.uniform(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in deploy_contract Owlto: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)
                continue
        return False
