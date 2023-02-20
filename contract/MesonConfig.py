from pyteal import Int, Bytes

class ConfigParams:
    
    def __init__(self):
        pass
    
    MESON_PROTOCOL_VERSION = Int(1)             # version 1
    MIN_BOND_TIME_PERIOD = Int(3600)            # 1 hour
    MAX_BOND_TIME_PERIOD = Int(7200)            # 2 hours
    LOCK_TIME_PERIOD = Int(1200)                # 20 minutes
    SHORT_COIN_TYPE = Int(0x011b)               # Algorand SLIP44: 	0x8000011b
            # See https://github.com/satoshilabs/slips/blob/master/slip-0044.md
    
    MAX_SWAP_AMOUNT = Int(100_000_000_000)      # 1e11 / 1e6 = $10k
    SERVICE_FEE_RATE = Int(10)
    
    ZERO_ADDRESS = Bytes(bytes.fromhex('00' * 32))          # 32 bytes
    LOCKED_SWAP_FINISH = Bytes(bytes.fromhex('11' * 38))    # 38 bytes
    POSTED_SWAP_EXPIRE = Bytes(bytes.fromhex('11' * 65))    # 65 bytes
    
    # ETH_SIGN_HEADER = Bytes("\x19Ethereum Signed Message:\n32");
    # ETH_SIGN_HEADER_52 = Bytes("\x19Ethereum Signed Message:\n52");
    # TRON_SIGN_HEADER = Bytes("\x19TRON Signed Message:\n32\n");
    # TRON_SIGN_HEADER_33 = Bytes("\x19TRON Signed Message:\n33\n");
    # TRON_SIGN_HEADER_53 = Bytes("\x19TRON Signed Message:\n53\n");

    # # REQUEST_TYPE_HASH = keccak256("bytes32 Sign to request a swap on Meson (Testnet)");
    # # RELEASE_TYPE_HASH = keccak256("bytes32 Sign to release a swap on Meson (Testnet)address Recipient");

    # # RELEASE_TO_TRON_TYPE_HASH = keccak256("bytes32 Sign to release a swap on Meson (Testnet)address Recipient (tron address in hex format)");
    