from pyteal import *


# Directly using global index to map:
def addSupportToken(tokenIndex: Int, enumIndex: Int) -> Int:
    # todo: onlyDeployer
    # todo: Optin
    
    #   Bytes('TokenIndex:17207135') -> Int(1)
    #   Bytes('EnumIndex:1') -> Int(17207135)
    return Seq(
        Assert(enumIndex < Int(256)),
        Assert(enumIndex != Int(0)),
        Assert(tokenIndex != Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex)) == Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex)) == Int(0)),
        App.globalPut(wrapTokenKeyName('EnumIndex:', enumIndex), tokenIndex),
        App.globalPut(wrapTokenKeyName('TokenIndex:', tokenIndex), enumIndex),
        App.localPut(
            Global.current_application_address(), 
            wrapTokenKeyName('MesonLP:', tokenIndex), 
            Int(0)
        ),
        Approve()
    )
    
    
def wrapTokenKeyName(suffix: str, index: Int) -> Bytes:
    return Concat(Bytes(suffix), Itob(index))


def getEnumIndex(tokenIndex: Int) -> Int:
    return App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex))


def getTokenIndex(enumIndex: Int) -> Int:
    return App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex))


def poolTokenBalance(
    lp: Bytes,
    enumIndex: Int,
) -> Int:
    tokenIndex = getTokenIndex(enumIndex)
    return App.localGet(lp, wrapTokenKeyName('MesonLP:', tokenIndex))



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
                        Btoi(Txn.application_args[1]), Btoi(Txn.application_args[2])
                    )
                ])
            ]
        )
    
    from test_run import TealApp
    ta = TealApp()
    ta.create_app(mesontoken_program_func, 'mesontokens.teal', [5, 5, 0, 0])
    ta.call_app(['addSupportToken', 0x183301, 3])