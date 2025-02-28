# 质押地址
STAKE_ADDRESS = "0x2c9C959516e9AAEdB2C748224a41249202ca8BE7"
# 质押的ABI
STAKE_ABI = [
    {
        "type": "function",
        "name": "stake",  # 使用任意函数名称
        "inputs": [],
        "outputs": [],
        "stateMutability": "payable",
        "signature": "0xd5575982"  # 重要：使用成功交易的确切签名
    }
]

