from pyteal import *


# Directly using global index to map:
def addSupportToken(tokenIndex: Bytes, enumIndex: Bytes) -> Int:
    # todo: onlyDeployer
    
    #   Bytes('TokenIndex:17207135') -> Int(1)
    #   Bytes('EnumIndex:1') -> Int(17207135)
    return Seq(
        Assert(Btoi(enumIndex) != Int(0)),
        Assert(Btoi(tokenIndex) != Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex)) == Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex)) == Int(0)),
        App.globalPut(wrapTokenKeyName('EnumIndex:', enumIndex), tokenIndex),
        App.globalPut(wrapTokenKeyName('TokenIndex:', tokenIndex), enumIndex),
        Approve()
    )
    
    
def wrapTokenKeyName(suffix: str, index: Bytes) -> Bytes:
    return Concat(Bytes(suffix), index)


def getEnumIndex(tokenIndex: Bytes):
    return App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex))


def getTokenIndex(enumIndex: Bytes):
    return App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex))


# getSupportedTokens: View explorer directly to get supported token list!



# -------------------------------------- For Test --------------------------------------
if __name__ == '__main__':
    
    def mesontoken_program_func():
        return Cond(
            [Txn.application_id() == Int(0), Approve()],
            [
                Txn.on_completion() == OnComplete.NoOp,
                Cond([
                    Txn.application_args[0] == Bytes("addSupportToken"),
                    addSupportToken(
                        Txn.application_args[1], Txn.application_args[2]
                    )
                ])
            ]
        )
    
    from test_run import TealApp
    ta = TealApp()
    ta.create_app(mesontoken_program_func, 'mesontokens.teal', [5, 5, 0, 0])
    ta.call_app(['addSupportToken', 0x183301, 3])