from pyteal import *

from MesonTokens import addSupportToken
from MesonSwap import postSwap, bondSwap, cancelSwap, executeSwap
from MesonPools import lock, unlock, release, depositAndRegister, deposit, withdraw


def initMainContract() -> Int:
    return Approve()


# ------------------------------------ Main Program ------------------------------------
def mesonMainFunc():
    return Cond(
        [
            Txn.application_id() == Int(0),
            initMainContract(),
        ],
        [
            Txn.on_completion() == OnComplete.OptIn,
            Approve(),
        ],
        [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
                Txn.on_completion() == OnComplete.DeleteApplication,  # TODO
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
                [
                    Txn.application_args[0] == Bytes("postSwap"),
                    postSwap(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Txn.application_args[5],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("bondSwap"),
                    bondSwap(Txn.application_args[1]),
                ],
                [
                    Txn.application_args[0] == Bytes("cancelSwap"),
                    cancelSwap(Txn.application_args[1]),
                ],
                [
                    Txn.application_args[0] == Bytes("lock"),
                    lock(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Txn.application_args[5],
                        Txn.accounts[1],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("unlock"),
                    unlock(
                        Txn.application_args[1],
                        Txn.application_args[2],
                    )
                ],
                [
                    Txn.application_args[0] == Bytes("release"),
                    release(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Txn.application_args[5],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("executeSwap"),
                    executeSwap(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Btoi(Txn.application_args[5]),
                        Txn.accounts[1],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("padding"),
                    Approve()
                ],
            ),
        ],
    )


# -------------------------------------- For Test --------------------------------------
if __name__ == "__main__":
    from test_run import TealApp

    ta = TealApp()
    open("./contract/compiled_teal/%s" % "meson.teal", "w").write(
        compileTeal(mesonMainFunc(), Mode.Application, version=8)
    )
    # ta.create_app(mesonPoolsMainFunc, 'mesonpools.teal', [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 0x183301, 3])
