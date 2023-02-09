from pyteal import *
from MesonConfig import ConfigParams as cp


# ---------------------------------- transfer and deposit ----------------------------------
def safeTransfer(
    tokenIndex: Int,
    recipient: Bytes,
    amount: Int,
    enumIndex: Int,
) -> Int:
    amount_adjust: Int = ScratchVar(TealType.uint64)
    return Seq(
        If(
            needAdjustAmount(enumIndex) == Int(1),
            amount_adjust.store(amount * Int(1_000_000_000_000)),
            amount_adjust.store(amount),
        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: tokenIndex,
                TxnField.asset_receiver: recipient,
                TxnField.asset_amount: amount_adjust.load(),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


# transferToContract: todo
# unsafeDepositToken: discard

def validateTokenReceived(
    txid: Int,
    tokenIndex: Int,
    amount: Int,
    enumIndex: Int,
) -> Int:
    amount_adjust: Int = ScratchVar(TealType.uint64)
    return Seq(
        Assert(amount > Int(0)),
        If(
            needAdjustAmount(enumIndex) == Int(1),
            amount_adjust.store(amount * Int(1_000_000_000_000)),
            amount_adjust.store(amount),
        ),
        And(
            Gtxn[txid].type_enum() == TxnType.AssetTransfer,
            Gtxn[txid].sender() == Txn.sender(),
            Gtxn[txid].asset_receiver() == Global.current_application_address(),
            Gtxn[txid].xfer_asset() == tokenIndex,
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

def itemFrom(
    item: str,
    encodedSwap: Bytes,
) -> Int:
    match item:  # match-case sentence is a new feature of python==3.10
        case "version":
            content = Substring(encodedSwap, Int(0), Int(1))
        case "amount":
            content = Substring(encodedSwap, Int(1), Int(6))
        case "salt":
            content = Substring(encodedSwap, Int(6), Int(16))
        case "saltUsing":
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
    saltUsing = itemFrom("saltUsing", encodedSwap)
    match extraItem:
        case "_serviceFee":
            content = (
                itemFrom("amount", encodedSwap) * cp.SERVICE_FEE_RATE / Int(10_000)
            )
        case "_willTransferToContract":
            content = saltUsing & Int(0x80) == Int(0)
        case "_feeWaived":
            content = saltUsing & Int(0x40) > Int(0)
        case "_signNonTyped":
            content = saltUsing & Int(0x08) > Int(0)

    return content



# ---------------------------- poolToken, lockedSwap, postedSwap ----------------------------

# `postedSwap` in format of `initiator:address(32)|lp:address(32)|tokenIndex:uint8(1)`
# Not the same one as in solidity!
  
def itemFromPosted(
    item: str,
    postedSwap: Bytes,
) -> Int:
    match item:
        case "initiator":
            content = Substring(postedSwap, Int(0), Int(32))
        case "lp":
            content = Substring(postedSwap, Int(32), Int(64))
        case "inToken":
            content = Substring(postedSwap, Int(64), Int(65))
        case _:
            assert False
    return content

# `lockedSwap` in format of `until:uint40(8)|lp:address(32)|tokenIndex:uint8(1)`
# Not the same one as in solidity!

def itemFromLocked(
    item: str,
    lockedSwap: Bytes, 
) -> Int:
    match item:
        case "until":
            content = Btoi(Substring(lockedSwap, Int(0), Int(5)))
        case "lp":
            content = Substring(lockedSwap, Int(5), Int(37))
        case "outToken":
            content = Substring(lockedSwap, Int(37), Int(38))
        case _:
            assert False
    return content
        

def lockedSwapFrom(
    until: Int,
    lp: Bytes,
    enumIndex: Int,
) -> Bytes:
    return Concat(Substring(until, Int(3), Int(8)), lp, Substring(enumIndex, Int(7), Int(8)))




# ---------------------------------- other utils functions ----------------------------------

#   function _needAdjustAmount(uint8 tokenIndex) internal pure returns (bool) {
#     return tokenIndex > 32 && tokenIndex < 255;
#   }
def needAdjustAmount(enumIndex: Int) -> Int:
    return And(enumIndex > Int(32), enumIndex < Int(255))


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
):
    return Keccak256(Concat(encodedSwap, initiator))



# ---------------------------------- signature ----------------------------------

def checkRequestSignature(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    signer: Bytes,
) -> Int:
    # todo
    return Int(1)


def checkReleaseSignature(
    encodedSwap: Bytes,
    recipient: Bytes,
    r_s: Int,
    v: Int,
    signer: Bytes,
) -> Int:
    # todo
    return Int(1)
