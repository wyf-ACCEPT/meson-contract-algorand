from typing import Union

from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *


def postSwap(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    postingValue: Bytes,
) -> Int:
    amount = itemFrom('amount', encodedSwap)
    delta = itemFrom('expireTs', encodedSwap) - Txn.first_valid_time()
    initiator = itemFromPosted('initiator', postingValue)
    lp = itemFromPosted('lp', postingValue)
    
    conditions = And(
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
        lp == Txn.sender(),
        checkRequestSignature(encodedSwap, r_s, v, initiator),
    )
    
    # todo: transferFrom?
    
    return Seq(
        Assert(conditions),
        Assert(App.box_create(encodedSwap, Int(65))),
        App.box_put(encodedSwap, postingValue),       
    )
