import { Algodv2 } from "algosdk";

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
    useTestnet(testnet: bool): void;
    getNetwork(id: string): PresetNetwork;
    createNetworkClient(id: string, urls?: string[], opts?: any): Algodv2;
}
declare const _default: MesonPresets;
export default _default;