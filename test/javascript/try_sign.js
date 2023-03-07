const { Wallet, SigningKey, utils, recoverAddress, keccak256 } = require('ethers')

main = async () => {

    // ------------------------ try signature ------------------------
    const decoder = new TextDecoder()
    const pk = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    const wallet = new Wallet(pk)
    const digest_hex = 'bd045242342bc4e3948a5029209b0e90e29e5a55dffff09113aa65b8ea997031'
    // const digest_hex = '7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb258626c2a6698ce7518c71a8e6c3c4c8739ac5a799c97997198b73d4cf694be601'
    const digest_bytes = Buffer.from(digest_hex, 'hex')

    const header = Buffer.from("\x19Ethereum Signed Message:\n32").reduce((accumulator, currentValue) => { return accumulator + currentValue.toString(16).padStart(2, '0') }, '')

    const digest_bytes_with_header = keccak256(Buffer.from(header + digest_hex, 'hex'))

    console.log(digest_bytes_with_header)

    console.log(digest_bytes)
    console.log(wallet.address)

    let s1 = await wallet.signMessage(digest_bytes)
    let s2 = wallet.signingKey.sign(digest_bytes).serialized

    console.log(recoverAddress(digest_bytes_with_header, s1))
    console.log(recoverAddress(digest_bytes, s2))


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

}

main()