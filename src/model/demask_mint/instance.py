import asyncio
import random
from eth_account import Account
from primp import AsyncClient
from web3 import AsyncWeb3
from web3.contract import Contract

from src.utils.constants import EXPLORER_URL, RPC_URL
from src.utils.config import Config
from loguru import logger

# 更新包含额外方法的NFT合约ABI
ERC1155_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "account", "type": "address"},
            {"internalType": "uint256", "name": "id", "type": "uint256"},
        ],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32[]", "name": "proof", "type": "bytes32[]"},
            {"internalType": "uint256", "name": "limit", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "buy",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "name": "mintedCountPerWallet",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class Demask:
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

        self.nft_contract_address = "0x2CDd146Aa75FFA605ff7c5Cc5f62D3B52C140f9c"  # Updated contract address for DeMask
        self.nft_contract: Contract = self.web3.eth.contract(
            address=self.nft_contract_address, abi=ERC1155_ABI
        )

    async def get_nft_balance(self) -> int:
        """
        Проверяет баланс NFT для текущего аккаунта
        Returns:
            int: количество NFT
        """
        try:
            # 尝试使用合约中的mintedCountPerWallet函数
            # 这个函数应该返回用户已经mint的NFT数量
            stage_id = 0  # 假设这是第一个阶段（可能需要调整）

            balance = await self.nft_contract.functions.mintedCountPerWallet(
                self.account.address, stage_id
            ).call()

            logger.info(f"[{self.account_index}] DeMask NFT balance: {balance}")
            return balance
        except Exception as e:
            # 如果第一个方法不起作用，尝试使用标准的balanceOf
            try:
                token_id = 46917  # ID代币来自交易
                balance = await self.nft_contract.functions.balanceOf(
                    self.account.address, token_id
                ).call()

                logger.info(
                    f"[{self.account_index}] DeMask NFT balance (via balanceOf): {balance}"
                )
                return balance
            except Exception as e2:
                # 如果两个方法都不起作用，记录错误并返回0
                logger.warning(
                    f"[{self.account_index}] Error checking NFT balance via mintedCountPerWallet: {e}"
                )
                logger.warning(
                    f"[{self.account_index}] Error checking NFT balance via balanceOf: {e2}"
                )

                # 检查交易历史作为最后的手段
                try:
                    # 获取合约地址的交易历史
                    tx_count = await self.web3.eth.get_transaction_count(
                        self.account.address
                    )

                    # 为了简单起见，只检查最后10笔交易
                    for i in range(max(0, tx_count - 10), tx_count):
                        try:
                            nonce = i
                            tx = await self.web3.eth.get_transaction_by_nonce(
                                self.account.address, nonce
                            )

                            # 如果交易是到我们的合约并且成功执行
                            if (
                                tx
                                and tx.to
                                and tx.to.lower() == self.nft_contract_address.lower()
                            ):
                                receipt = await self.web3.eth.get_transaction_receipt(
                                    tx.hash
                                )
                                if receipt and receipt.status == 1:
                                    # 找到到DeMask合约的成功交易
                                    logger.info(
                                        f"[{self.account_index}] Found successful transaction to DeMask contract"
                                    )
                                    return (
                                        1  # 返回1，表示NFT已经mint
                                    )
                        except Exception:
                            continue
                except Exception as e3:
                    logger.warning(
                        f"[{self.account_index}] Error checking transaction history: {e3}"
                    )

                # 如果所有方法都不起作用，返回0
                return 0

    async def mint(self):
        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                balance = await self.get_nft_balance()

                random_amount = random.randint(
                    self.config.DEMASK.MAX_AMOUNT_FOR_EACH_ACCOUNT[0],
                    self.config.DEMASK.MAX_AMOUNT_FOR_EACH_ACCOUNT[1],
                )

                if balance >= random_amount:
                    logger.success(
                        f"[{self.account_index}] DeMask NFT already minted: {balance} NFTS"
                    )
                    return True

                logger.info(f"[{self.account_index}] Minting DeMask NFT")

                # 准备mint交易，使用buy方法
                # 使用空proof，limit=1000000，amount=1
                mint_txn = await self.nft_contract.functions.buy(
                    [], 1000000, 1
                ).build_transaction(
                    {
                        "from": self.account.address,
                        "value": self.web3.to_wei(0.1, "ether"),  # Оплата 0.1 MON
                        "nonce": await self.web3.eth.get_transaction_count(
                            self.account.address
                        ),
                        "maxFeePerGas": await self.web3.eth.gas_price,
                        "maxPriorityFeePerGas": await self.web3.eth.gas_price,
                    }
                )

                # 签名交易
                signed_txn = self.web3.eth.account.sign_transaction(
                    mint_txn, self.private_key
                )

                # 发送交易
                tx_hash = await self.web3.eth.send_raw_transaction(
                    signed_txn.raw_transaction
                )

                # 等待确认
                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

                if receipt["status"] == 1:
                    logger.success(
                        f"[{self.account_index}] Successfully minted DeMask NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return True
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to mint DeMask NFT. TX: {EXPLORER_URL}{tx_hash.hex()}"
                    )
                    return False

            except Exception as e:
                random_pause = random.randint(
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                    self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                )
                logger.error(
                    f"[{self.account_index}] Error in mint on DeMask: {e}. Sleeping for {random_pause} seconds"
                )
                await asyncio.sleep(random_pause)

        return False
