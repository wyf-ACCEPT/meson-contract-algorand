from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initMesonPools() -> Int:
    return Approve()


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
        App.localPut(lp, wrapTokenKeyName("MesonLP:", assetId), amount),
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
        App.localPut(
            lp,
            wrapTokenKeyName("MesonLP:", assetId),
            poolTokenBalance(lp, tokenIndex) + amount,
        ),
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
        App.localPut(
            lp,
            wrapTokenKeyName("MesonLP:", assetId),
            poolTokenBalance(lp, tokenIndex) - amount,
        ),
        safeTransfer(assetId, lp, amount, tokenIndex),
        Approve(),
    )


# Step 2.
def lock(
    encodedSwap: Bytes,
    r: Int,
    sv: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    outChain = itemFrom("outChain", encodedSwap)
    version = itemFrom("version", encodedSwap)
    lockAmount = itemFrom("amount", encodedSwap) - itemFrom("feeForLP", encodedSwap)
    expireTs = itemFrom("expireTs", encodedSwap)
    until = Txn.first_valid_time() + cp.LOCK_TIME_PERIOD
    swapId = getSwapId(encodedSwap, initiator)
    lp = Txn.sender()
    tokenIndexOut = itemFrom("outToken", encodedSwap)
    assetIdOut = getAssetId(tokenIndexOut)
    lockedSwap = lockedSwapFrom(until, lp, tokenIndexOut)

    conditions = And(
        outChain == cp.SHORT_COIN_TYPE,
        version == cp.MESON_PROTOCOL_VERSION,
        until < expireTs - Int(300),  # 5 minutes     # todo: check if it's 300 or 300,000
        checkRequestSignature(encodedSwap, r, sv, initiator),
        poolTokenBalance(lp, tokenIndexOut) > lockAmount,
    )

    return Seq(
        Assert(conditions),
        App.localPut(
            lp,
            wrapTokenKeyName("MesonLP:", assetIdOut),
            poolTokenBalance(lp, tokenIndexOut) - lockAmount,
        ),
        Assert(App.box_create(swapId, Int(38))),
        App.box_put(swapId, lockedSwap),
        Approve(),
    )


# Step 3.
def release(
    encodedSwap: Bytes,
    r: Int,
    sv: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    # todo: Txn.sender() == <tx.origin>?
    # todo: _onlyPremiumManager
    feeWaived = extraItemFrom("_feeWaived", encodedSwap)
    expireTs = itemFrom("expireTs", encodedSwap)
    swapId = getSwapId(encodedSwap, initiator)
    tokenIndexOut = itemFrom("outToken", encodedSwap)
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
        checkReleaseSignature(encodedSwap, recipient, r, sv, initiator),
    )

    return Seq(
        Assert(conditions),
        App.box_put(swapId, cp.LOCKED_SWAP_FINISH),
        releaseAmount.store(
            itemFrom("amount", encodedSwap) - itemFrom("feeForLP", encodedSwap)
        ),
        If(
            Not(feeWaived),
            Seq(
                releaseAmount.store(releaseAmount.load() - serviceFee),
                App.globalPut(
                    wrapTokenKeyName("ProtocolFee:", assetIdOut),
                    App.globalGet(wrapTokenKeyName("ProtocolFee:", assetIdOut))
                    + serviceFee,
                ),
            ),
        ),  # todo: transferToContract
        safeTransfer(assetIdOut, recipient, releaseAmount.load(), tokenIndexOut),
        Approve(),
    )

