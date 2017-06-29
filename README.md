# iTC Reporter

## What?
This script mimics the official **iTunes Connect Reporter** by Apple which is used to automatically **retrieve Sales- and Financial Reports** for your App Store sales.
It is written in pure Python and **doesn't need a Java runtime installation**.
Opposed to Apple's tool, it can fetch iTunes Connect login credentials from the macOS Keychain in order to **tighten security** a bit. Also, it goes the extra mile and **unzips the downloaded reports**.

## Why?

### Once upon a time, there was autoingestion …
In the past, Apple has provided a tool called **autoingest** for automated retrieving of sales reports from iTunes Connect. While this tool worked quite reliably, it needed a full blown Java Runtime Environment installed. 

### … nowadays, it's all about Reporter
Apple has shut down autoingestion on December 13th, 2016. Fortunately, it has been replaced by a new and a bit more streamlined tool called **Reporter**. Unfortunately, **Reporter** is based on Java, too. It also suffers from a minor but annoying security threat as it needs to read iTunes Connect login credentials from a cleartext file.

### Java really is a sledge hammer to crack this nut
There really is no compelling reason to employ a Java tool with its somewhat heavyweight dependency on JRE in order to download a few reports from iTunes Connect. Apart from the Apple backend engineering staff really being into Java, apparently. Also, storing login credentials in cleartext isn't state of the art anymore.

**iTC Reporter** (this Python script), on the other hand, solves both problems. It is written in pure Python and doesn't need Java or any external dependencies to function. Also, it can optionally read the iTC access token from the OS X Keychain (though it generally is still advisable to use an extra Apple ID specifically created for retrieving reports!).

## How?

The argument names and values of this script have mostly been chosen to be consistent with [Apple's documentation for Reporter](https://help.apple.com/itc/appsreporterguide/). To get a quick overview, here is the output of `./reporter.py -h`: 
```text
usage: reporter.py [-h] [-a ACCOUNT] [-m {Normal,Robot.XML}] -u USERID
                   (-p PASSWORD_KEYCHAIN_ITEM | -P PASSWORD | -T ACCESS_TOKEN | -t ACCESS_TOKEN_KEYCHAIN_ITEM)
                   {getStatus,getAccounts,getVendors,getVendorsAndRegions,getFinancialReport,getSalesReport,getSubscriptionReport,getSubscriptionEventReport,getSubscriberReport,getNewsstandReport,getOptInReport}
                   ...

Reporting tool for querying Sales- and Financial Reports from iTunes Connect

optional arguments:
  -h, --help            show this help message and exit
  -a ACCOUNT, --account ACCOUNT
                        account number (needed if your Apple ID has access to
                        multiple accounts; for a list of your account numbers,
                        use the 'getAccounts' command)
  -m {Normal,Robot.XML}, --mode {Normal,Robot.XML}
                        output format: plain text or XML (defaults to
                        'Normal')

required arguments:
  -u USERID, --userid USERID
                        Apple ID for use with iTunes Connect
  -t ACCESS_TOKEN_KEYCHAIN_ITEM, --access-token-keychain-item ACCESS_TOKEN_KEYCHAIN_ITEM
                        name of the macOS Keychain item that holds the access
                        token
  -T ACCESS_TOKEN, --access-token ACCESS_TOKEN
                        Access token (can be generated in iTunes Connect -
                        Sales & Trends - Reports - About Reports)
  -p PASSWORD_KEYCHAIN_ITEM, --password-keychain-item PASSWORD_KEYCHAIN_ITEM
                        DEPRECATED: name of the macOS Keychain item that holds
                        the Apple ID password (cannot be used together with
                        -P)
  -P PASSWORD, --password PASSWORD
                        DEPRECATED: Apple ID password (cannot be used together
                        with -p)

commands:
  Specify the task you want to be carried out (use -h after a command's name
  to get additional help for that command)

  {getStatus,getAccounts,getVendors,getVendorsAndRegions,getFinancialReport,getSalesReport,getSubscriptionReport,getSubscriptionEventReport,getSubscriberReport,getNewsstandReport,getOptInReport}
    getStatus           check if iTunes Connect is available for queries
    getAccounts         fetch a list of accounts accessible to the Apple ID
                        given in -u
    getVendors          fetch a list of vendors accessible to the Apple ID
                        given in -u
    getVendorsAndRegions
                        fetch a list of financial reports you can download by
                        vendor number and region
    getFinancialReport  download a financial report file for a specific region
                        and fiscal period
    getSalesReport      download a summary sales report file for a specific
                        date range
    getSubscriptionReport
                        download a subscription report file for a specific day
    getSubscriptionEventReport
                        download an aggregated subscriber activity report file
                        for a specific day
    getSubscriberReport
                        download a transaction-level subscriber activity
                        report file for a specific day
    getNewsstandReport  download a magazines & newspapers report file for a
                        specific date range
    getOptInReport      download contact information for customers who opt in
                        to share their contact information with you

For a detailed description of report types, see
http://help.apple.com/itc/appssalesandtrends/#/itc37a18bcbf
```

### Usage examples

#### Obtaining an iTunes Connect access token
Apple will enforce the use of access tokens instead of passwords for **Reporter** by August 2017. To generate an access token for an Apple ID, log in to iTunes Connect using the Apple ID that you plan to use with `reporter.py`. Go to *Sales and Trends > Reports*, then click on the tooltip next to *About Reports*. Click *Generate Access Token*.
Tokens expire after 180 days, so you are going to have to renew them in the same way.

#### Querying accessible accounts
Because your Apple ID could have access to multiple accounts, you will sometimes need to specify the account number you’d like to use. Use the following query to find out which accounts are available:

```sh
./reporter.py -u your@apple-id.com -T youraccesstoken getAccounts Sales
```
The result is a list of account numbers you can then specify with the `-a` or `--account` argument in later queries regarding sales reports. Similarly, you'd use `getAccounts Finance` in order to find out account numbers that can be used for financial report queries.

#### Fetching the access token from the Keychain
But what about the cleartext token following the `-T` parameter? If you want to store and fetch it securely from the macOS Keychain instead, you need to create a new keychain item. To do so, open the **Keychain Access.app**, select the default keychain, press **⌘N** and fill in your Apple ID's access token. The item name you set for this new keychain entry is going to be what you have to supply for `-t` (now lowercase!).

The following example queries iTunes Connect's availability status for financial reports while fetching the access token from the Keychain item named "iTC Access":

```sh
./reporter.py -u your@apple-id.com -t "iTC Access" getStatus Finance
```

#### Retrieving reports
Let's get to the point of this tool now: Retrieving reports from iTunes Connect.
To find out which vendor numbers you can query, you'll first need to get a list of available vendors, using (one of) the account number(s) you have found out with `getAccounts` before:

```sh
./reporter.py -u your@apple-id.com -t "iTC Access" --account 2821955 getVendors
```

The resulting vendor number(s) can then be used to get the actual reports. In the following example, a sales report listing the sales of a single day (2016/08/18) for vendor 85442109 is going to be retrieved: 

```sh
./reporter.py -u your@apple-id.com -t "iTC Access" -a 2821955 getSalesReport 85442109 Daily 20160818
```

Likewise, the following example fetches a financial report for sales in the US region in the first period of 2016 (according to Apple's fiscal calendar):

```sh
./reporter.py -u your@apple-id.com -t "iTC Access" -a 2821955 getFinancialReport 85442109 US 2016 01
```

These examples should do for a quick introduction. Don't forget to read Apple's [reference documentation](https://help.apple.com/itc/appsreporterguide/) for **Reporter**. Also, you can get further help for a specific command by supplying `-h` after the command's name. For example: 

```sh
./reporter.py getFinancialReport -h
```

## What's still missing
There seem to be [additional report types](http://help.apple.com/itc/contentreporterguide/en.lproj/static.html) available for retrieving Apple Music related data, but I wonder if anybody using this script would really need it.

## Obligatory disclaimer

There is absolutely no warranty. I do not guarantee in any way that this tool works as intended or is fully compatible with Apple's official **Reporter** tool.

## Pull Requests
Neither English nor Python are my native language – corrective PRs (even for style only) are very welcome!
