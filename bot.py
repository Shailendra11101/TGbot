import logging
import time

from telegram import __version__ as TG_VER
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import json

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

BSC_RPC_URL = 'https://data-seed-prebsc-1-s1.binance.org:8545/'  # Binance Smart Chain testnet RPC URL

# Load the ABI from the JSON file
with open('abi.json', 'r') as abi_file:
    abi = json.load(abi_file)

with open('ERC20abi.json', 'r') as ERC20abi_file:
    ERC20abi = json.load(ERC20abi_file)

logger = logging.getLogger(__name__)
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))
user_wallets = {}
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

router_address = w3.to_checksum_address('0x9ac64cc6e4415144c455bd8e4837fea55603e5c3')  # Replace with your router contract address
router_contract = w3.eth.contract(address=router_address, abi=abi)


# Replace the following with your actual values
WBNB = w3.to_checksum_address('0xae13d989dac2f0debff460ac112a837c89baa7cd')  # WBNB contract address
BUSD = w3.to_checksum_address("0x78867BbEeF44f2326bF8DDd1941a4439382EF2A7")
DEADLINE = 100000000000
GAS_LIMIT = 200000  # You can adjust the gas limit as needed
GAS_PRICE = Web3.to_wei('5', 'gwei')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id

    # Check if the user already has a wallet
    if user_id in user_wallets:
        await update.message.reply_html("You already have a wallet.")
    else:
        # Generate a new Ethereum wallet for the user
        wallet = w3.eth.account.create()
        address = wallet.address
        private_key = wallet.key.hex()

        # Save the wallet details for the user
        user_wallets[user_id] = (address, private_key)
        context.user_data['address'] = address
        context.user_data['private_key'] = private_key
        await update.message.reply_html(
            f"Hi {user.mention_html()}!\n"
            f"Your wallet address: {address}\n"
            f"Your private key: {private_key}",
            reply_markup=ForceReply(selective=True),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

# Define states for the conversation
TOKEN_ADDRESS, AMOUNT = range(2)

def execute_swap(amount_in, path, privateKey, publicKey):

    data = router_contract.functions.swapExactETHForTokens(
            0,
            path,
            publicKey,
            DEADLINE,
        ).build_transaction({
        'chainId': 97,  # Replace with the chain ID (BSC testnet)
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(publicKey),
        'value': amount_in,
        })
    signed_txn = w3.eth.account.sign_transaction(data, privateKey)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()

def execute_sell_swap(amount_in, path, privateKey, publicKey):

    data = router_contract.functions.swapExactETHForTokens(
            0,
            path,
            publicKey,
            1690861779,
        ).build_transaction({
        'chainId': 97,  # Replace with the chain ID (BSC testnet)
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(publicKey),
        'value': amount_in,
        })
    signed_txn = w3.eth.account.sign_transaction(data, privateKey)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return tx_hash.hex()

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the buy conversation when the user clicks on the /buy command."""
    user = update.effective_user
    user_id = user.id

    # Check if the user has a wallet
    if user_id not in user_wallets:
        await update.message.reply_html("You need to start first to create a wallet.")
        return ConversationHandler.END
    print("=============0===========1")

    # Prompt the user for the token address
    await update.message.reply_text("Please enter the token address:")
    return TOKEN_ADDRESS

async def receive_buy_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the token address and prompt for the amount."""
    token_address = update.message.text
    print("=============1===========1")

    # Save the token address in the conversation context
    context.user_data['token_address'] = token_address

    # Prompt the user for the amount
    await update.message.reply_text("Please enter the amount of tokens you want to buy:")
    return AMOUNT

async def receive_buy_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive the amount and process the buy request."""
    amount = update.message.text

    # Get the token address from the conversation context
    token_address = context.user_data.get('token_address')
    print("========================1")
    # Implement the buy logic here
    # For example, you can use the token_address and amount to execute the buy transaction on Ethereum

    address = context.user_data.get('address')
    private_key = context.user_data.get('private_key')

    amount_in_wei = w3.to_wei(amount, 'ether')
    print(amount_in_wei,"===============")
    # wbnb, tokenaddress
    swap_path = [WBNB,BUSD]
    try:
        tx_hash = execute_swap(amount_in_wei, swap_path, private_key, address)
        print('Transaction Hash:', tx_hash)
        await update.message.reply_text(f"You bought {amount} tokens with token address: {token_address}. Transaction Hash: {tx_hash}")
    except Exception as e:
        # If an exception occurs, send the error message back to the Telegram bot
        error_message = f"An error occurred during the transaction: {str(e)}"
        await update.message.reply_text(error_message)

    return ConversationHandler.END

def execute_swap(amount_in, path, privateKey, publicKey):
    try:
        data = router_contract.functions.swapExactETHForTokens(
            0,
            path,
            publicKey,
            DEADLINE,
        ).build_transaction({
            'chainId': 97,  # Replace with the chain ID (BSC testnet)
            'gas': GAS_LIMIT,
            'gasPrice': GAS_PRICE,
            'nonce': w3.eth.get_transaction_count(publicKey),
            'value': amount_in,
        })
        signed_txn = w3.eth.account.sign_transaction(data, privateKey)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        # If an exception occurs, raise it to the calling function
        raise e

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id

    # Check if the user has a wallet
    if user_id not in user_wallets:
        await update.message.reply_html("You need to start first to create a wallet.")
        return ConversationHandler.END
    print("=============0===========1")

    # Prompt the user for the token address
    await update.message.reply_text("Please enter the token address:")
    return TOKEN_ADDRESS

async def receive_sell_token_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the token address and prompt for the amount."""
    token_address = update.message.text
    print("=============1===========1")

    # Save the token address in the conversation context
    context.user_data['token_address'] = token_address

    # Prompt the user for the amount
    await update.message.reply_text("Please enter the amount of tokens you want to buy:")
    return AMOUNT

async def receive_sell_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive the amount and process the buy request."""
    amount = update.message.text

    # Get the token address from the conversation context
    token_address = context.user_data.get('token_address')
    print("========================1")
    # Implement the buy logic here
    # For example, you can use the token_address and amount to execute the buy transaction on Ethereum

    address = context.user_data.get('address')
    private_key = context.user_data.get('private_key')

    amount_in_wei = w3.to_wei(amount, 'ether')
    print(amount_in_wei,"===============")
    
    # AmountIn = "0x" + parseInt(reserveIn).toString(16)
    ERCToken = w3.eth.contract(address=BUSD, abi=ERC20abi)

    data = ERCToken.functions.approve(
            router_address,
            amount_in_wei,
        ).build_transaction({
        'chainId': 97,  # Replace with the chain ID (BSC testnet)
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(address),
        })
    signed_txn = w3.eth.account.sign_transaction(data, private_key)

    try:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        print('Approve Transaction Hash:', tx_hash.hex())
    except Exception as e:
        # If an exception occurs, send the error message back to the Telegram bot
        error_message = f"An error occurred during the transaction: {str(e)}"
        await update.message.reply_text(error_message)



    time.sleep(20)

    print('Approve Transaction Hash:', tx_hash.hex())
    path = [BUSD, WBNB]

    data = router_contract.functions.swapExactTokensForETH(
            amount_in_wei,
            0,
            path,
            address,
            DEADLINE,
        ).build_transaction({
        'chainId': 97,  # Replace with the chain ID (BSC testnet)
        'gas': GAS_LIMIT,
        'gasPrice': GAS_PRICE,
        'nonce': w3.eth.get_transaction_count(address),
        })
    signed_txn = w3.eth.account.sign_transaction(data, private_key)
    
    try:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        # return tx_hash.hex()
        await update.message.reply_text(f"You want to buy {amount} tokens with token address: {token_address}. Transaction hash: {tx_hash.hex()}")
    except Exception as e:
        # If an exception occurs, send the error message back to the Telegram bot
        error_message = f"An error occurred during the transaction: {str(e)}"
        await update.message.reply_text(error_message)

    return ConversationHandler.END

    


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("6378306025:AAFVewxsIgkHrCCSANOLWvYkxp2kXidBb78").build()
    # Create a ConversationHandler with the states and handlers
    buy_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('buy', buy)],
        states={
            TOKEN_ADDRESS: [MessageHandler(filters.TEXT, receive_buy_token_address)],
            AMOUNT: [MessageHandler(filters.TEXT, receive_buy_amount)],
        },
        fallbacks=[],
    )

    sell_conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('sell', sell)],
        states={
            TOKEN_ADDRESS: [MessageHandler(filters.TEXT, receive_sell_token_address)],
            AMOUNT: [MessageHandler(filters.TEXT, receive_sell_amount)],
        },
        fallbacks=[],
    )


    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    # application.add_handler(CommandHandler("buy", buy_conversation_handler))
    application.add_handler(buy_conversation_handler)
    application.add_handler(sell_conversation_handler)

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()