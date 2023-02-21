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
    sv: Int,
    initiator: Bytes,
) -> Int:
    inChain = _decodeSwap(encodedSwap, "inChain")
    version = _decodeSwap(encodedSwap, "version")
    amount = _decodeSwap(encodedSwap, "amount")
    delta = _decodeSwap(encodedSwap, "expireTs") - Txn.first_valid_time()
    from_address = Txn.sender()  # todo
    lp_not_bonded = cp.ZERO_ADDRESS
    tokenIndexIn = _decodeSwap(encodedSwap, "inToken")
    assetIdIn = _getAssetId(tokenIndexIn)
    postingValue = _postedSwapFrom(lp_not_bonded, initiator, from_address)

    conditions = And(
        # TODO: check encodedSwap length = 32
        version == cp.MESON_PROTOCOL_VERSION,
        inChain == cp.SHORT_COIN_TYPE,
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
        _checkRequestSignature(encodedSwap, r, sv, initiator),
        _validateTokenReceived(
            Int(1), assetIdIn, amount, tokenIndexIn
        ),  # the user must call `AssetTransfer` at Gtxn[1], and call `postSwap` at Gtxn[0]
    )

    return Seq(
        Assert(conditions),
        Assert(App.box_create(encodedSwap, Int(65))), # XXX: what is 65?
        App.box_put(encodedSwap, postingValue),
        Approve(),
    )


# Step 1.2: After user called `postSwap`, the lp should call `bondSwap`.
def bondSwap(encodedSwap: Bytes):
    return Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        Assert(_itemFromPosted("lp", postedSwap_get.value()) == cp.ZERO_ADDRESS),
        App.box_replace(encodedSwap, Int(32), Txn.sender()),
        Approve(),
    )


# Step 4.
def executeSwap(
    encodedSwap: Bytes,
    r: Int,
    sv: Int,
    depositToPool: Int,
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    expireTs = _decodeSwap(encodedSwap, "expireTs")
    amount = _decodeSwap(encodedSwap, "amount")
    tokenIndexIn = _decodeSwap(encodedSwap, "inToken")
    assetIdIn = _getAssetId(tokenIndexIn)
    postedSwap = ScratchVar(TealType.bytes)
    initiator = _itemFromPosted("initiator", postedSwap.load())
    lp = _itemFromPosted("lp", postedSwap.load())

    postedSwap_value = Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        postedSwap_get.value(),
    )
    conditions = And(
        postedSwap.load() != cp.POSTED_SWAP_EXPIRE,
        _checkReleaseSignature(encodedSwap, recipient, r, sv, initiator),
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
                _storageKey("MesonLP:", assetIdIn),
                poolTokenBalance(lp, tokenIndexIn) + amount,
            ),
            _safeTransfer(assetIdIn, lp, amount, tokenIndexIn),
        ),
        Approve(),
    )

