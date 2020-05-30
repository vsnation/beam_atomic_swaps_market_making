## Atomic Swap BEAM BTC LTC Quick Deploy Guide

### Electrum BTC

Download electrum from <link>https://electrum.org/#download</link>

<code>wget https://download.electrum.org/[VERSION]/[FILE_NAME] | tar -xvf</code>

<code>cd [ELECTRUM_FOLDER]</code>

#####Restore wallet by seed
<code>electrum restore "[SEED]"</code>

####Set settings to config file
<code>vim ~/.electrum/config</code>

Paste 
<pre>{
    "config_version": 3,
    "rpcpassword": "PASSWORD",
    "rpchost": "0.0.0.0",
    "rpcport": 7777,
    "rpcuser": "user",
    "decimal_point": 8,
    "dynamic_fees": true,
    "fee_level": 4
}</pre>

##### Start Daemon
<code>electrum daemon start</code>

##### Load wallet
<code>electrum daemon load_wallet</code>

##### Stop Daemon
<code>electrum daemon start</code>

### Set swap settings for BTC in beam cli wallet

This command should be used in your wallet dir. Use <code>cd beam-wallet</code>

<code>./beam-wallet set_swap_settings --swap_coin=btc --swap_wallet_user=user --swap_wallet_pass=PASSWORD --swap_feerate=90000 --active_connection=electrum --electrum_seed="[SEED]" --electrum_addr=127.0.0.1:7777</code>

#

### Electrum LTC

Download electrum-ltc from <link>https://electrum-ltc.org</link>

<code>wget https://electrum-ltc.org/download/Electrum-LTC-[VERSION] | tar -xvf</code>

<code>cd Electrum-LTC-[VERSION]</code>

##### Restore wallet by seed
<code>electrum-ltc restore "[SEED]"</code>


#### Set settings to config file
<code>vim ~/.electrum-ltc/config</code>

Paste 
<pre>{
    "config_version": 3,
    "rpcpassword": "PASSWORD",
    "rpchost": "0.0.0.0",
    "rpcport": 7778,
    "rpcuser": "user",
    "decimal_point": 8,
    "dynamic_fees": true,
    "fee_level": 4
}</pre>

##### Load wallet
<code>electrum-ltc daemon load_wallet</code>

##### Start Daemon
<code>electrum-ltc daemon start</code>

##### Stop Daemon
<code>electrum-ltc daemon start</code>


### Set swap settings for LTC in beam cli wallet

This command should be used in your wallet dir. Use <code>cd beam-wallet</code>

<code>./beam-wallet set_swap_settings --swap_coin=ltc --swap_wallet_user=user --swap_wallet_pass=PASSWORD --swap_feerate=90000 --active_connection=electrum --electrum_seed="[SEED]" --electrum_addr=127.0.0.1:7778</code>

