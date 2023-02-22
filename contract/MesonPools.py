from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initMesonPools() -> Int:
    return Approve()


def updateBalanceOfPool(
    lp: Bytes,
    assetId: Int,
    balance: Int,
):
    return App.localPut(lp, storageKey("MesonLP:", assetId), balance)


def depositAndRegister(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = getTokenIndex(assetId)

    conditions = And(
        validateTokenReceived(Int(1), assetId, amount, tokenIndex),
        poolTokenBalance(lp, tokenIndex) == Int(0),
    )

    return Seq(
        Assert(conditions),
        updateBalanceOfPool(lp, assetId, amount),
        Approve(),
    )


# todo: this function (maybe) can merge with the above one
def deposit(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = getTokenIndex(assetId)

    return Seq(
        Assert(validateTokenReceived(Int(1), assetId, amount, tokenIndex)),
        updateBalanceOfPool(lp, assetId, poolTokenBalance(lp, tokenIndex) + amount),
        Approve(),
    )


# Step 0.3: lp withdraw
def withdraw(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = getTokenIndex(assetId)

    return Seq(
        Assert(poolTokenBalance(lp, tokenIndex) >= amount),
        updateBalanceOfPool(lp, assetId, poolTokenBalance(lp, tokenIndex) - amount),
        safeTransfer(assetId, lp, amount, tokenIndex),
        Approve(),
    )


# Step 2.
def lock(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    outChain = decodeSwap("outChain", encodedSwap)
    version = decodeSwap("version", encodedSwap)
    lockAmount = decodeSwap("amount", encodedSwap) - decodeSwap("feeForLP", encodedSwap)
    expireTs = decodeSwap("expireTs", encodedSwap)
    until = Txn.first_valid_time() + cp.LOCK_TIME_PERIOD
    swapId = getSwapId(encodedSwap, initiator)
    lp = Txn.sender()
    tokenIndexOut = decodeSwap("outToken", encodedSwap)
    assetIdOut = getAssetId(tokenIndexOut)
    lockedSwap = lockedSwapFrom(lp, until)

    conditions = And(
        outChain == cp.SHORT_COIN_TYPE,
        version == cp.MESON_PROTOCOL_VERSION,
        until < expireTs - Int(300),  # 5 minutes     # todo: check if it's 300 or 300,000
        checkRequestSignature(encodedSwap, r_s, v, initiator),
        poolTokenBalance(lp, tokenIndexOut) > lockAmount,
    )

    return Seq(
        Assert(conditions),
        updateBalanceOfPool(lp, assetIdOut, poolTokenBalance(lp, tokenIndexOut) - lockAmount),
        Assert(App.box_create(swapId, Int(37))),
        App.box_put(swapId, lockedSwap),
        Approve(),
    )


# Step 3.
def release(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    # todo: Txn.sender() == <tx.origin>?
    # todo: _onlyPremiumManager
    feeWaived = extraItemFrom("_feeWaived", encodedSwap)
    expireTs = decodeSwap("expireTs", encodedSwap)
    swapId = getSwapId(encodedSwap, initiator)
    tokenIndexOut = decodeSwap("outToken", encodedSwap)
    assetIdOut = getAssetId(tokenIndexOut)
    serviceFee = extraItemFrom("_serviceFee", encodedSwap)
    releaseAmount = ScratchVar(TealType.uint64)

    conditions = And(
        Seq(
            lockedSwap_get := App.box_get(swapId),
            Assert(lockedSwap_get.hasValue()),
            lockedSwap_get.value() != cp.LOCKED_SWAP_FINISH,
        ),
        recipient != cp.ZERO_ADDRESS,
        expireTs > Txn.first_valid_time(),
        checkReleaseSignature(encodedSwap, recipient, r_s, v, initiator),
    )

    return Seq(
        Assert(conditions),
        App.box_put(swapId, cp.LOCKED_SWAP_FINISH),
        releaseAmount.store(
            decodeSwap("amount", encodedSwap) - decodeSwap("feeForLP", encodedSwap)
        ),
        If(
            Not(feeWaived),
            Seq(
                releaseAmount.store(releaseAmount.load() - serviceFee),
                App.globalPut(
                    storageKey("ProtocolFee:", assetIdOut),
                    App.globalGet(storageKey("ProtocolFee:", assetIdOut))
                    + serviceFee,
                ),
            ),
        ),  # todo: transferToContract
        safeTransfer(assetIdOut, recipient, releaseAmount.load(), tokenIndexOut),
        Approve(),
    )


# ------------------------------------ Main Program of Pools ------------------------------------
def mesonPoolsMainFunc():
    return Cond(
        [
            Txn.application_id() == Int(0),
            initMesonPools(),
        ],
        [
            Txn.on_completion() == OnComplete.OptIn,
            Approve(),
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
                    Txn.application_args[0] == Bytes("lock"),
                    lock(
                        Txn.application_args[1],
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Txn.accounts[1],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("release"),
                    release(
                        Txn.application_args[1],
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Txn.accounts[1],
                        Txn.accounts[2],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("depositAndRegister"),
                    depositAndRegister(
                        Btoi(Txn.application_args[1]),
                        Txn.assets[0],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("deposit"),
                    deposit(
                        Btoi(Txn.application_args[1]),
                        Txn.assets[0],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("withdraw"),
                    withdraw(
                        Btoi(Txn.application_args[1]),
                        Txn.assets[0],
                    ),
                ],
            ),
        ],
    )


# -------------------------------------- For Test --------------------------------------
if __name__ == "__main__":
    from test_run import TealApp

    ta = TealApp()
    open("./compiled_teal/%s" % "mesonpools.teal", "w").write(
        compileTeal(mesonPoolsMainFunc(), Mode.Application, version=8)
    )
    # ta.create_app(mesonPoolsMainFunc, 'mesonpools.teal', [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 0x183301, 3])
