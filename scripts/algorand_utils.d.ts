import { Algodv2, Indexer, Account, SuggestedParams } from "algosdk";
import { Wallet } from "ethers";

declare class AlgorandUtils {
  constructor();

  client: Algodv2;
  indexer: Indexer;
  on_complete_param: number;
  usdc_index: number;
  usdt_index: number;
  request_typehash: string;
  release_typehash: string;
  encoder: TextEncoder;
  alice: Account;
  bob: Account;
  carol: Account;
  initiator_wallet: Wallet;
  initiator_address: string;
  initiator_buffer: Buffer;
  meson_contract_code: string;

  load_mnemonic(string: string): Account;
  intToUint8Array(num: number, bytes_length: number): Uint8Array;
  listToUint8ArrayList(list: (string | number | Buffer)[]): Uint8Array[];
  get_expire_ts(delay?: number): number;
  build_encoded(amount: number, expireTs: number, outToken: string, inToken: string, return_bytes?: boolean, salt?: string, fee?: string): Uint8Array | string;
  get_swapID(encoded_hexstring: string, initiator: string, return_bytes?: boolean): Uint8Array | string;
  buffer_to_hex(buffer: Buffer): string;
  hex_timestamp_to_date(timestamp_hex: string): string;
  decode_algorand_address(algo_addr: string): string;
  sign_request(encoded_hexstring: string): [Buffer, Buffer, number];
  sign_release(encoded_hexstring: string, recipient_algo_addr: string): [Buffer, Buffer, number];
  sp_func(): Promise<SuggestedParams>;
  show_account_info(): Promise<void>;
  submit_transaction(private_key: string, unsigned_txn: any): Promise<any>;
  submit_transaction_group(private_key: string, unsigned_txns: any[]): Promise<any>;
  compile_program(source_code: string): Promise<Uint8Array>;
  show_boxes(meson_index: number, is_in_chain: boolean): Promise<void>;
}

module.exports = { AlgorandUtils }
