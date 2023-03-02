from pyteal import *
from MesonConfig import ConfigParams as cp


# ---------------------------------- transfer and deposit ----------------------------------
def safeTransfer(
    assetId: Int,
    recipient: Bytes,
    amount: Int,
    tokenIndex: Int,
):
    amount_adjust: Int = ScratchVar(TealType.uint64)
    return Seq(
        If(
            needAdjustAmount(tokenIndex) == Int(1),
            amount_adjust.store(amount * Int(1_000_000_000_000)),
            amount_adjust.store(amount),
        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: assetId,
                TxnField.asset_receiver: recipient,
                TxnField.asset_amount: amount_adjust.load(),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


# transferToContract: TODO
# unsafeDepositToken: discard


def validateTokenReceived(
    txid: Int,
    assetId: Int,
    amount: Int,
    tokenIndex: Int,
) -> Int:
    amount_adjust: Int = ScratchVar(TealType.uint64)
    return Seq(
        Assert(amount > Int(0)),
        If(
            needAdjustAmount(tokenIndex) == Int(1),
            amount_adjust.store(amount * Int(1_000_000_000_000)),
            amount_adjust.store(amount),
        ),
        And(
            Gtxn[txid].type_enum() == TxnType.AssetTransfer,
            Gtxn[txid].sender() == Txn.sender(),
            Gtxn[txid].asset_receiver() == Global.current_application_address(),
            Gtxn[txid].xfer_asset() == assetId,
            Gtxn[txid].asset_amount() == amount,
        ),
    )


# ---------------------------------- encodedSwap processing ----------------------------------

# In pyteal, the type of `encodedSwap` should be `Bytes`, because type `Int` cannot be the key of Box variable.
# `encodedSwap`(Bytes: length=32): `version:uint8|amount:uint40|salt:uint80|fee:uint40|expireTs:uint40|outChain:uint16|outToken:uint8|inChain:uint16|inToken:uint8`

# ============ example ============
# origin format: [bytes32]
# \x01\x00\x01\xe8H\x00\xc0\x00\x00\x00\x00\x00\xe7U& \x00\x00\x00\x00\x00\x00c\xd5\x00B#)\x02\x02\xca
# hex format [uint256, hex64]:
# (0x)010001e84800c00000000000e755262000000000000063d5004223290202ca22
# split values: 0x|01|0001e84800|c00000000000e7552620|0000000000|0063d50042|2329|02|02ca|22
# split variables: 0x|version|amount|salt|fee|expireTs|outChain|outToken|inChain|inToken
# index(start-end): 0x | 0:1 | 1:6 | 6:16 | 16:21 | 21:26 | 26:28 | 28:29 | 29:31 | 31:32
# index(start-length): 0x | 0,1 | 1,5 | 6,10 | 16,5 | 21,5 | 26,2 | 28,1 | 29,2 | 31,1
def decodeSwap(
    field: str,
    encodedSwap: Bytes,
) -> Int:
    match field:  # match-case sentence is a new feature of python==3.10
        case "version":
            content = Substring(encodedSwap, Int(0), Int(1))
        case "amount":
            content = Substring(encodedSwap, Int(1), Int(6))
        case "salt":
            content = Substring(encodedSwap, Int(6), Int(16))
        case "saltHeader":
            content = Substring(encodedSwap, Int(6), Int(7))
        case "saltData":
            content = Substring(encodedSwap, Int(8), Int(16))
        case "feeForLP":
            content = Substring(encodedSwap, Int(16), Int(21))
        case "expireTs":
            content = Substring(encodedSwap, Int(21), Int(26))
        case "outChain":
            content = Substring(encodedSwap, Int(26), Int(28))
        case "outToken":
            content = Substring(encodedSwap, Int(28), Int(29))
        case "inChain":
            content = Substring(encodedSwap, Int(29), Int(31))
        case "inToken":
            content = Substring(encodedSwap, Int(31), Int(32))
        case _:
            assert False

    return Btoi(content)


def extraItemFrom(
    extraItem: str,
    encodedSwap: Bytes,
) -> Int:
    saltHeader = decodeSwap("saltHeader", encodedSwap)
    match extraItem:
        case "_serviceFee":
            content = (
                decodeSwap("amount", encodedSwap) * cp.SERVICE_FEE_RATE / Int(10_000)
            )
        case "_willTransferToContract":
            content = saltHeader & Int(0x80) == Int(0)
        case "_feeWaived":
            content = saltHeader & Int(0x40) > Int(0)
        case "_signNonTyped":
            content = saltHeader & Int(0x08) > Int(0)

    return content


# ---------------------------- poolToken, lockedSwap, postedSwap ----------------------------

# `postedSwap(84)` in format of `lp:address(32)|initiator:eth_address(20)|from_address:address(32)`
# Not the same one as in solidity!
def itemFromPosted(
    field: str,
    postedSwap: Bytes,  # Bytes(65)
) -> Int:
    match field:
        case "lp":
            content = Substring(postedSwap, Int(0), Int(32))
        case "initiator":
            content = Substring(postedSwap, Int(32), Int(52))
        case "from_address":
            content = Substring(postedSwap, Int(52), Int(84))
        case _:
            assert False
    return content


def postedSwapFrom(
    lp: Bytes,
    initiator: Bytes,
    from_address: Bytes,
) -> Bytes:
    return Concat(lp, initiator, from_address)


# `lockedSwap(69)` in format of `lp:address(32)|until:uint40(5)|recipient:address(32)`
# Not the same one as in solidity!
def itemFromLocked(
    field: str,
    lockedSwap: Bytes,  # Bytes(41)
) -> Int:
    match field:
        case "lp":
            content = Substring(lockedSwap, Int(0), Int(32))
        case "until":
            content = Btoi(Substring(lockedSwap, Int(32), Int(37)))
        case "recipient":
            content = Substring(lockedSwap, Int(37), Int(69))
        case _:
            assert False
    return content


def lockedSwapFrom(
    lp: Bytes,
    until: Int,
    recipient: Bytes,
) -> Bytes:
    return Concat(lp, Substring(Itob(until), Int(3), Int(8)), recipient)


# ---------------------------------- other utils functions ----------------------------------
def needAdjustAmount(tokenIndex: Int) -> Int:
    return And(tokenIndex > Int(32), tokenIndex < Int(255))


# `abi.encode` in solidity:
# (uint256 10, address 0x7A58c0Be72BE218B41C608b7Fe7C5bB630736C71, string "0xAA", uint[2] [5, 6])
#  -> 0x
# 000000000000000000000000000000000000000000000000000000000000000a
# 0000000000000000000000007a58c0be72be218b41c608b7fe7c5bb630736c71
# 00000000000000000000000000000000000000000000000000000000000000a0
# 0000000000000000000000000000000000000000000000000000000000000005
# 0000000000000000000000000000000000000000000000000000000000000006
# 0000000000000000000000000000000000000000000000000000000000000004
# 3078414100000000000000000000000000000000000000000000000000000000

# `abi.encodePacked` in solidity:
# (uint256 10, address 0x7A58c0Be72BE218B41C608b7Fe7C5bB630736C71, string "0xAA", uint[2] [5, 6])
#  -> 0x
# 000000000000000000000000000000000000000000000000000000000000000a
# 7a58c0be72be218b41c608b7fe7c5bb630736c71
# 30784141
# 0000000000000000000000000000000000000000000000000000000000000005
# 0000000000000000000000000000000000000000000000000000000000000006


def getSwapId(
    encodedSwap: Bytes,
    initiator: Bytes,
) -> Bytes:  # Bytes(32)
    return Keccak256(Concat(encodedSwap, initiator))


# ---------------------------------- signature ----------------------------------
def isEthAddr(addrEth: Bytes) -> Int:
    return Len(addrEth) == Int(20)


def ethAddrFromAlgorandAddr(addrAlgo: Bytes) -> Bytes:
    return Substring(addrAlgo, Int(0), Int(20))


def ethAddrFromPubkey(pk: Bytes) -> Bytes:
    return Seq(
        Assert(Len(pk) == Int(64)),
        Substring(Keccak256(pk), Int(12), Int(32))
    )


def recoverEthAddr(
    digest: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
) -> Bytes:
    pkMultiValue = EcdsaRecover(EcdsaCurve.Secp256k1, digest, v, r, s)
    pk = pkMultiValue.outputReducer(lambda X, Y: Concat(X, Y))  # Concat the return MultiValue
    return ethAddrFromPubkey(pk)
    

def checkRequestSignature(
    encodedSwap: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
    signer: Bytes,
) -> Int:
    messageHash = Keccak256(encodedSwap)
    typeHash = cp.REQUEST_TYPEHASH   # TODO: Add more if-else branches (TRON, signNonTyped)
    digest = Keccak256(Concat(typeHash, messageHash))
    recovered = recoverEthAddr(digest, r, s, v)
    
    return And(
        isEthAddr(signer),
        recovered == signer,
    )


def checkReleaseSignature(
    encodedSwap: Bytes,
    recipient: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
    signer: Bytes,
) -> Int:
    messageRecipientHash = Keccak256(Concat(encodedSwap, recipient))
    typeHash = cp.RELEASE_TYPEHASH   # TODO: Add more if-else branches (TRON, signNonTyped)
    digest = Keccak256(Concat(typeHash, messageRecipientHash))
    recovered = recoverEthAddr(digest, r, s, v)
    
    return And(
        isEthAddr(signer),
        recovered == signer,
    )



# -------------------------------------- For Test --------------------------------------
def mesonHelpersMainFunc():
    return Cond(
        [
            Txn.application_id() == Int(0),
            Approve(),
        ],
        [
            Txn.on_completion() == OnComplete.OptIn, 
            Approve()
        ],
        [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
                Txn.on_completion() == OnComplete.DeleteApplication,
            ),
            Reject(),
        ],
        [
            Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [
                    Txn.application_args[0] == Bytes("checkRequest"),
                    Seq(
                        Assert(
                            checkRequestSignature(
                                Txn.application_args[1],
                                Txn.application_args[2],
                                Txn.application_args[3],
                                Btoi(Txn.application_args[4]),
                                Txn.application_args[5],
                            )
                        ), 
                        Approve()
                    )
                ],
                [
                    Txn.application_args[0] == Bytes("checkRelease"),
                    Seq(
                        Assert(
                            checkReleaseSignature(
                                Txn.application_args[1],
                                Txn.application_args[2],
                                Txn.application_args[3],
                                Txn.application_args[4],
                                Btoi(Txn.application_args[5]),
                                Txn.application_args[6],
                            )
                        ), 
                        Approve()
                    )
                ],
                [
                    Int(1),
                    Approve()
                ]
            )
        ]
    )


if __name__ == "__main__":
    from test_run import TealApp

    ta = TealApp()
    open("./contract/compiled_teal/%s" % "mesonhelpers.teal", "w").write(
        compileTeal(mesonHelpersMainFunc(), Mode.Application, version=8)
    )

    import time
    from web3.auto import w3
    from Crypto.Hash import keccak

    private_key_origin = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    digest_origin = 'bd045242342bc4e3948a5029209b0e90e29e5a55dffff09113aa65b8ea997031'
    request_type = "bytes32 Sign to request a swap on Meson (Testnet)"
    release_type = "bytes32 Sign to release a swap on Meson (Testnet)address Recipient"
    request_typehash = bytes.fromhex('7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb25')
    release_typehash = bytes.fromhex('d23291d9d999318ac3ed13f43ac8003d6fbd69a4b532aeec9ffad516010a208c')
    
    def keccak256(bytes_str):
        keccak_func = keccak.new(digest_bits=256)
        hash_value = keccak_func.update(bytes.fromhex(bytes_str) if type(bytes_str) == str else bytes_str)
        return hash_value.hexdigest()
    
    def get_expire_ts(delay=90):   # default to 90 minutes
        return int(time.time()) + 60*delay

    def build_encoded(amount: int, expireTs: int, outToken, inToken, 
                    salt='c00000000000e7552620', fee='0000000000', return_bytes=True):
        assert amount < 0x1111111111
        version = '01'
        amount_string = hex(amount)[2:].rjust(10, '0')
        expireTs_string = hex(expireTs)[2:].rjust(10, '0')
        outChain = '011b'
        inChain = '011b'
        encoded_string = ''.join([
            '0x', version, amount_string, salt, fee, expireTs_string, outChain, outToken, inChain, inToken
        ])
        return bytes.fromhex(encoded_string[2:]) if return_bytes else encoded_string
    
    
    phil_private_key = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    initiator = bytes.fromhex('2ef8a51f8ff129dbb874a0efb021702f59c1b211')
    encodedSwap = build_encoded(50 * 1_000_000, get_expire_ts(), '02', '01')

    digest_request = bytes.fromhex(keccak256(request_typehash + bytes.fromhex(keccak256(encodedSwap))))
    signed_message = w3.eth.account._sign_hash(digest_request, phil_private_key)
    r_int, s_int, v = signed_message.r, signed_message.s, signed_message.v - 27
    r, s = int.to_bytes(r_int, 32, 'big'), int.to_bytes(s_int, 32, 'big')
    
    print('Encoded     Hash: ', keccak256(encodedSwap))
    print('Request TypeHash: ', request_typehash.hex())
    print('Digest          : ', digest_request)
    print('r, s, v         : ', r.hex(), s.hex(), v, sep='\n')
    # print('\n', keccak256(encodedSwap), request_typehash.hex(), digest, r.hex(), s.hex(), v, sep='\n')
    
    ta.create_app(mesonHelpersMainFunc, 'mesonhelpers.teal', [5, 5, 0, 0])
    ta.call_app_group([['checkRequest', encodedSwap, r, s, v, initiator], ['padding1'], ['padding2'], ['padding3'], ['padding4'], ['padding5'], ['padding6'], ['padding7']])