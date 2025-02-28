from tabulate import tabulate
from typing import List, Optional
from loguru import logger

from src.utils.config import Config, WalletInfo


def print_wallets_stats(config: Config):
    """
     输出所有钱包的统计信息以表格形式显示
    """
    try:
        # 排序钱包按索引
        sorted_wallets = sorted(config.WALLETS.wallets, key=lambda x: x.account_index)

        # 准备数据用于表格
        table_data = []
        total_balance = 0
        total_transactions = 0

        for wallet in sorted_wallets:
            # 屏蔽私钥（最后5个字符）
            masked_key = "•" * 3 + wallet.private_key[-5:]

            total_balance += wallet.balance
            total_transactions += wallet.transactions

            row = [
                str(wallet.account_index),  # 只是没有前导零的数字
                wallet.address,  # 完整地址
                masked_key,
                f"{wallet.balance:.4f} MON",
                f"{wallet.transactions:,}",  # 格式化数字
            ]
            table_data.append(row)

        # 如果有数据 - 打印表格和统计数据
        if table_data:
            # 创建表格标题
            headers = [
                "№ Account",
                "Wallet Address",
                "Private Key",
                "Balance (MON)",
                "Total Txs",
            ]

            # 创建表格，使用更美观的格式
            table = tabulate(
                table_data,
                headers=headers,
                tablefmt="double_grid",  # 更美观的边界
                stralign="center",  # 居中对齐字符串
                numalign="center",  # 居中对齐数字
            )

            # 计算平均值
            wallets_count = len(sorted_wallets)
            avg_balance = total_balance / wallets_count
            avg_transactions = total_transactions / wallets_count

            # 打印表格和统计数据
            logger.info(
                f"\n{'='*50}\n"
                f"         Wallets Statistics ({wallets_count} wallets)\n"
                f"{'='*50}\n"
                f"{table}\n"
                f"{'='*50}\n"
                f"{'='*50}"
            )

            logger.info(f"Average balance: {avg_balance:.4f} MON")
            logger.info(f"Average transactions: {avg_transactions:.1f}")
            logger.info(f"Total balance: {total_balance:.4f} MON")
            logger.info(f"Total transactions: {total_transactions:,}")
        else:
            logger.info("\nNo wallet statistics available")

    except Exception as e:
        logger.error(f"Error while printing statistics: {e}")
