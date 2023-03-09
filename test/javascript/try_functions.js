const { Wallet, SigningKey, utils, recoverAddress, keccak256, assert } = require('ethers')
const base32Decode = require('base32-decode')

main = async () => {

    // ------------------------ try signature ------------------------
    // const pk = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    // const wallet = new Wallet(pk)
    // const digest_hex = 'bd045242342bc4e3948a5029209b0e90e29e5a55dffff09113aa65b8ea997031'
    // const digest_bytes = Buffer.from(digest_hex, 'hex')

    // const header = Buffer.from("\x19Ethereum Signed Message:\n32").reduce((accumulator, currentValue) => { return accumulator + currentValue.toString(16).padStart(2, '0') }, '')
    // const digest_bytes_with_header = keccak256(Buffer.from(header + digest_hex, 'hex'))

    // console.log(digest_bytes_with_header)

    // console.log(digest_bytes)
    // console.log(wallet.address)

    // let s1 = await wallet.signMessage(digest_bytes)
    // let s2 = wallet.signingKey.sign(digest_bytes).serialized

    // console.log(recoverAddress(digest_bytes_with_header, s1))
    // console.log(recoverAddress(digest_bytes, s2))


    // ------------------------ turn int to Uint8Array ------------------------
    // const encoder = new TextEncoder()
    // console.log(encoder.encode('addSupportToken'))

    // function intToUint8Array(num, bytes) {
    //     let buffer = new ArrayBuffer(bytes);
    //     let view = new DataView(buffer);
    //     for (let i = bytes-1; i >= 0; i--) {
    //         view.setUint8(i, num & 0xff);
    //         num >>= 8;
    //     }
    //     return new Uint8Array(buffer);
    // }

    // let num = 1572;
    // let uint8Array = intToUint8Array(num, 8);
    // console.log(uint8Array); // Uint8Array [ 210, 2, 150, 73 ]


    // ------------------------ utils functions ------------------------

    // function get_expire_ts(delay = 90) {
    //     return Math.floor(Date.now() / 1e3 + 60 * delay)
    // }

    // function build_encoded(amount, expireTs, outToken, inToken, return_bytes = true,
    //     salt = 'c00000000000e7552620', fee = '0000000000') {
    //     let version = '01'
    //     let amount_string = amount.toString(16).padStart(10, '0')
    //     let expireTs_string = expireTs.toString(16).padStart(10, '0')
    //     let outChain = '011b'
    //     let inChain = '011b'
    //     let encoded_hexstring = [version, amount_string, salt, fee, expireTs_string, outChain, outToken, inChain, inToken].join('')
    //     let encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
    //     assert(amount < 0x0fffffffff, "Amount should less than $68719.476735!")
    //     assert(encoded_hexstring.length == 64, "Encodedswap length should be 64!")
    //     if (return_bytes) return encoded_bytes
    //     else return encoded_hexstring
    // }

    // function get_swapID(encoded_hexstring, initiator, return_bytes = true) {
    //     let concat = encoded_hexstring + initiator
    //     assert(concat.length == 104 && typeof(concat) == 'string', "")
    //     let hash_hexstring = keccak256(Buffer.from(concat, 'hex')).slice(2)
    //     let hash_bytes = Buffer.from(hash_hexstring, 'hex')
    //     if (return_bytes) return hash_bytes
    //     else return hash_hexstring
    // }


    // const amount_transfer = 50 * 1_000_000
    // let encoded_hexstring = build_encoded(amount_transfer, get_expire_ts(), '02', '01', false)
    // let encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
    // console.log(encoded_hexstring)

    // const initiator = '2ef8a51f8ff129dbb874a0efb021702f59c1b211'
    // let swapId = get_swapID(encoded_hexstring, initiator, false)
    // console.log(swapId)


    // ------------------------ sign ------------------------

    // const request_type = "bytes32 Sign to request a swap on Meson (Testnet)"
    // const release_type = "bytes32 Sign to release a swap on Meson (Testnet)address Recipient"
    // const request_typehash = '7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb25'
    // const release_typehash = 'd23291d9d999318ac3ed13f43ac8003d6fbd69a4b532aeec9ffad516010a208c'

    // const initiator_private_key = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    // const initiator = '2ef8a51f8ff129dbb874a0efb021702f59c1b211'
    // const encoded_bytes = Buffer.from('010002faf080c00000000000e755262000000000000064080dd4011b02011b01', 'hex')

    // let encoded_hash = keccak256(encoded_bytes).slice(2)
    // let digest_request = Buffer.from(keccak256(Buffer.from(request_typehash + encoded_hash, 'hex')).slice(2), 'hex')

    // console.log(digest_request)

    // let initiator_wallet = new Wallet(initiator_private_key)
    // let sig = initiator_wallet.signingKey.sign(digest_request)

    // console.log(sig.r, sig.s, sig.v - 27)
    // console.log(Buffer.from(sig.r.slice(2), 'hex'), Buffer.from(sig.s.slice(2), 'hex'), sig.v - 27, '\n')


    // function sign_request(content_bytes, private_key) {
    //     let content_hash = keccak256(content_bytes).slice(2)
    //     let digest_request = Buffer.from(keccak256(Buffer.from(request_typehash + content_hash, 'hex')).slice(2), 'hex')
    //     let wallet = new Wallet(private_key)
    //     let sig = wallet.signingKey.sign(digest_request)
    //     return [Buffer.from(sig.r.slice(2), 'hex'), Buffer.from(sig.s.slice(2), 'hex'), sig.v - 27]
    // }

    // [r, s, v] = sign_request(encoded_bytes, initiator_private_key)
    // console.log(r, s, v)

    // function decode_algorand_address(algo_addr) {
    //     let buffer_address = new Buffer.from(base32Decode(algo_addr, 'RFC4648').slice(0, -4))
    //     let hex_address = buffer_address.reduce((accumulator, currentValue) => { 
    //         return accumulator + currentValue.toString(16).padStart(2, '0') 
    //     }, '')
    //     return hex_address
    // }

    // r = decode_algorand_address('GZ4IJXXNRFT23E6SLUOSSUWN2LUDFQTX4F6SXF5EP27LFWTOWHPFANLYIQ')
    // console.log(r)
    // console.log(base32Decode)

    // def decode_algorand_address(algo_addr):
    // return base64.b32decode(algo_addr + '======')[:-4]


    // ------------------------ convert timestamp ------------------------
    // new Date(0x0064095c29 * 1e3)
}

main()