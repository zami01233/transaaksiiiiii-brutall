import json
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3, HTTPProvider
from eth_account import Account
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

CONFIG_FILE = 'config.json'
PROXY_FILE = 'proxy.txt'
TX_LOG = 'tx.log'


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def display_header():
    clear_screen()
    print("""
    █████╗ ███╗   ██╗ █████╗ ███╗   ███╗
   ██╔══██╗████╗  ██║██╔══██╗████╗ ████║
   ███████║██╔██╗ ██║███████║██╔████╔██║
   ██╔══██║██║╚██╗██║██╔══██║██║╚██╔╝██║
   ██║  ██║██║ ╚████║██║  ██║██║ ╚═╝ ██║
   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝    by ANAM
    """)
    print("🔗 WORKKKKK\n")


def save_config(rpc_url, chain_id, private_key, block_explorer):
    config = {'rpc_url': rpc_url, 'chain_id': chain_id, 'private_key': private_key, 'block_explorer': block_explorer}
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None


def get_user_input():
    rpc_url = input("🧠 RPC URL: ")
    chain_id = int(input("🔗 Chain ID: "))
    private_key = input("🔑 Private Key: ")
    block_explorer = input("🔍 Block Explorer (ex: https://explorer.io/tx/): ")
    return rpc_url, chain_id, private_key, block_explorer


def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    return proxies


def create_web3_with_proxy(rpc_url, proxy_url):
    session = Session()
    session.proxies = {'http': proxy_url, 'https': proxy_url}
    retries = Retry(total=3, backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return Web3(HTTPProvider(rpc_url, session=session))


def get_gas_settings(w3):
    gas_price = w3.eth.gas_price
    gas_price_gwei = w3.from_wei(gas_price, 'gwei')
    gas_limit = 21000

    print(f"\n🔥 Gas Price: {gas_price_gwei:.2f} Gwei | Gas Limit: {gas_limit}")
    confirm = input("Gunakan gas ini? (y/n): ").lower()
    if confirm != 'y':
        gas_price_gwei = float(input("Gas Price (Gwei): "))
        gas_price = w3.to_wei(gas_price_gwei, 'gwei')
        gas_limit = int(input("Gas Limit: "))
    return gas_price, gas_limit


def log_transaction(status, to_addr, tx_hash, proxy_used):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status_emoji = "✅" if status else "❌"
    with open(TX_LOG, 'a') as f:
        f.write(f"[{now}] {status_emoji} TX to: {to_addr} | Proxy: {proxy_used or 'NO PROXY'} | TX Hash: {tx_hash}\n")


def send_transaction_flash(w3, from_account, to_address, amount, nonce, chain_id, gas_price, gas_limit, block_explorer, proxy_used):
    try:
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': w3.to_wei(amount, 'ether'),
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': chain_id
        }
        signed_tx = from_account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_url = f"{block_explorer}{tx_hash.hex()}"
        print(f"✅ TX ke {to_address} | {tx_url}")
        log_transaction(True, to_address, tx_url, proxy_used)
    except Exception as e:
        print(f"❌ Gagal TX ke {to_address} | Error: {str(e)}")
        log_transaction(False, to_address, "-", proxy_used)


def send_transactions_flash_loop(rpc_url, from_account, amount, chain_id, block_explorer, gas_price, gas_limit, proxies):
    batch_count = 1
    while True:
        wallets = [Account.create() for _ in range(100)]
        to_addresses = [wallet.address for wallet in wallets]
        nonce = Web3(Web3.HTTPProvider(rpc_url)).eth.get_transaction_count(from_account.address)

        print(f"\n📦 BATCH {batch_count} | Mengirim ke {len(to_addresses)} wallet...\n")

        with ThreadPoolExecutor(max_workers=20) as executor:
            for i, to_addr in enumerate(to_addresses):
                proxy = proxies[i % len(proxies)] if proxies else None
                try:
                    w3 = create_web3_with_proxy(rpc_url, proxy) if proxy else Web3(Web3.HTTPProvider(rpc_url))
                except:
                    w3 = Web3(Web3.HTTPProvider(rpc_url))
                    proxy = None
                executor.submit(send_transaction_flash,
                                w3, from_account, to_addr, amount, nonce + i, chain_id,
                                gas_price, gas_limit, block_explorer, proxy)
        batch_count += 1
        time.sleep(random.randint(1, 2))


def get_config():
    config = load_config()
    if config:
        use = input("mau jalan ga nih ? (y/n): ").lower()
        if use == 'y':
            return config['rpc_url'], config['chain_id'], config['private_key'], config['block_explorer']
    rpc_url, chain_id, private_key, block_explorer = get_user_input()
    save_config(rpc_url, chain_id, private_key, block_explorer)
    return rpc_url, chain_id, private_key, block_explorer


def main():
    display_header()
    rpc_url, chain_id, private_key, block_explorer = get_config()
    proxies = load_proxies()

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("❌ Gagal koneksi RPC.")
        return

    net_chain = w3.eth.chain_id
    if net_chain != chain_id:
        print(f"⚠️ Chain ID mismatch! Config: {chain_id} | RPC: {net_chain}")
        if input("Tetap lanjut? (y/n): ").lower() != 'y':
            return

    from_account = Account.from_key(private_key)
    gas_price, gas_limit = get_gas_settings(w3)
    amount = 0.0000013  # ETH

    send_transactions_flash_loop(rpc_url, from_account, amount, chain_id, block_explorer, gas_price, gas_limit, proxies)


if __name__ == "__main__":
    main()
