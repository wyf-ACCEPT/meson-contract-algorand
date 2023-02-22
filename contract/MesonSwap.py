from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initMesonSwap() -> Int:
    return Approve()


# Step 1.1: Different to the one in solidity, this `postSwap` can only called by user!
def postSwap(
    encodedSwap: Bytes,
    r: Int,
    s_v: Int,
    initiator: Bytes,   # This is an etheruem address
) -> Int:
    inChain = decodeSwap("inChain", encodedSwap)
    version = decodeSwap("version", encodedSwap)
    amount = decodeSwap("amount", encodedSwap)
    delta = decodeSwap("expireTs", encodedSwap) - Txn.first_valid_time()
    from_address = Txn.sender()  # todo
    lp_not_bonded = cp.ZERO_ADDRESS
    tokenIndexIn = decodeSwap("inToken", encodedSwap)
    assetIdIn = getAssetId(tokenIndexIn)
    postingValue = postedSwapFrom(lp_not_bonded, initiator, from_address)

    conditions = And(
        version == cp.MESON_PROTOCOL_VERSION,
        inChain == cp.SHORT_COIN_TYPE,
        # TODO: check encodedSwap length = 32
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
        checkRequestSignature(encodedSwap, r, s_v, initiator),
        validateTokenReceived(
            Int(1), assetIdIn, amount, tokenIndexIn
        ),  # the user must call `AssetTransfer` at Gtxn[1], and call `postSwap` at Gtxn[0]
    )

    return Seq(
        Assert(conditions),
        Assert(App.box_create(encodedSwap, Int(84))),
        App.box_put(encodedSwap, postingValue),
        Approve(),
    )


# Step 1.2: After user called `postSwap`, the lp should call `bondSwap`.
def bondSwap(encodedSwap: Bytes):
    return Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        Assert(itemFromPosted("lp", postedSwap_get.value()) == cp.ZERO_ADDRESS),
        App.box_replace(encodedSwap, Int(32), Txn.sender()),
        Approve(),
    )


# Step 4.
def executeSwap(
    encodedSwap: Bytes,
    r: Int,
    s_v: Int,
    depositToPool: Int,
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    expireTs = decodeSwap("expireTs", encodedSwap)
    amount = decodeSwap("amount", encodedSwap)
    tokenIndexIn = decodeSwap("inToken", encodedSwap)
    assetIdIn = getAssetId(tokenIndexIn)
    postedSwap = ScratchVar(TealType.bytes)
    initiator = itemFromPosted("initiator", postedSwap.load())
    lp = itemFromPosted("lp", postedSwap.load())

    postedSwap_value = Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        postedSwap_get.value(),
    )
    conditions = And(
        postedSwap.load() != cp.POSTED_SWAP_EXPIRE,
        checkReleaseSignature(encodedSwap, recipient, r, s_v, initiator),
    )

    return Seq(
        postedSwap.store(postedSwap_value),
        Assert(conditions),
        If(
            expireTs < Txn.first_valid_time() + cp.MIN_BOND_TIME_PERIOD,
            Assert(App.box_delete(encodedSwap)),
            App.box_put(encodedSwap, cp.POSTED_SWAP_EXPIRE),
        ),
        If(
            depositToPool,
            App.localPut(
                lp,
                storageKey("MesonLP:", assetIdIn),
                poolTokenBalance(lp, tokenIndexIn) + amount,
            ),
            safeTransfer(assetIdIn, lp, amount, tokenIndexIn),
        ),
        Approve(),
    )


# ------------------------------------ Main Program of Swap ------------------------------------
def mesonSwapMainFunc():
    return Cond(
        [
            Txn.application_id() == Int(0),
            initMesonSwap(),
        ],
        [
            Txn.on_completion() == OnComplete.OptIn, Approve()
        ],
        [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
                Txn.on_completion() == OnComplete.DeleteApplication,  # todo
            ),
            Reject(),
        ],
        [
            Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [
                    Txn.application_args[0] == Bytes("addSupportToken"),
                    addSupportToken(
                        Txn.assets[0],
                        Btoi(Txn.application_args[1]),
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("postSwap"),
                    postSwap(
                        Txn.application_args[1],
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Txn.application_args[4],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("bondSwap"),
                    bondSwap(Txn.application_args[1]),
                ],
                [
                    Txn.application_args[0] == Bytes("executeSwap"),
                    executeSwap(
                        Txn.application_args[1],
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Btoi(Txn.application_args[4]),
                        Txn.accounts[1],
                    ),
                ],
            ),
        ],
    )


# -------------------------------------- For Test --------------------------------------
if __name__ == "__main__":
    from test_run import TealApp

    ta = TealApp()
    open("./compiled_teal/%s" % "mesonswap.teal", "w").write(
        compileTeal(mesonSwapMainFunc(), Mode.Application, version=8)
    )
    # ta.create_app(mesonSwapMainFunc, 'mesonswap.teal', [5, 5, 0, 0])
    # ta.call_app(['optIn'])
