export interface PresetToken {
    addr: string;
    name?: string;
    symbol: string;
    decimals: number;
    tokenIndex: number;
    disabled?: boolean;
}
export interface PresetNetwork {
    id: string;
    name: string;
    chainId: string;
    slip44: string;
    shortSlip44: string;
    extensions?: string[];
    addressFormat: string;
    url?: string;
    explorer?: string;
    mesonAddress: string;
    uctAddress?: string;
    nativeCurrency?: {
        name?: string;
        symbol: string;
        decimals: number;
    };
    tokens: PresetToken[];
    metadata?: any;
}
export declare class MesonPresets {
    constructor(networks?: PresetNetwork[]);
    useTestnet(testnet: any): void;
    getNetwork(id: string): PresetNetwork;
    createNetworkClient

    // useTestnet(testnet: any): void;
    // getAllNetworks(): PresetNetwork[];
    // getNetwork(id: string): PresetNetwork;
    // getNetworkFromShortCoinType(shortCoinType: string): PresetNetwork;
    // getNetworkFromChainId(chainId: string): PresetNetwork;
    // getTokensForNetwork(id: string, includeDisabled?: boolean): PresetToken[];
    // getToken(networkId: string, tokenIndex: number): PresetToken;
    // getV0Token(networkId: string, tokenIndex: number): PresetToken;
    // getTokenByCategory(networkId: string, category?: string): PresetToken;
    // getTokenCategory(networkId: string, tokenIndex: number): "usdc" | "usdt" | "busd" | "pod" | "uct";
    // getNetworkToken(shortCoinType: string, tokenIndex: number, version?: number): {
    //     network: PresetNetwork;
    //     token?: any;
    // };
    // parseInOutNetworkTokens(encoded: string): {
    //     swap?: undefined;
    //     from?: undefined;
    //     to?: undefined;
    // } | {
    //     swap: Swap;
    //     from: {
    //         network: PresetNetwork;
    //         token?: any;
    //     };
    //     to: {
    //         network: PresetNetwork;
    //         token?: any;
    //     };
    // };
    // createMesonClient(id: string, client: any): MesonClient;
    // _getProviderClassAndConstructParams(id: string, urls?: string[], opts?: any): any[];
    createNetworkClient(id: string, urls?: string[], opts?: any): providers.Provider;
    // disposeMesonClient(id: string): void;
    // getMesonClientFromShortCoinType(shortCoinType: string): MesonClient;
    // checkSwapStatus(encoded: string, initiator?: string, options?: any): Promise<[
    //     {
    //         status: PostedSwapStatus;
    //         initiator?: string;
    //         provider?: string;
    //     },
    //     {
    //         status: LockedSwapStatus;
    //         initiator?: string;
    //         provider?: string;
    //         until?: number;
    //     }?
    // ]>;
}
declare const _default: MesonPresets;
export default _default;