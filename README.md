# iTC Reporter

## What?
This script mimics the official **iTunes Connect Reporter** by Apple which is used to automatically **retrieve Sales- and Financial Reports** for your App Store sales.
It is written in pure Python and **doesn't need a Java runtime installation**.
Opposed to Apple's tool, it can fetch iTunes Connect login credentials from the macOS Keychain in order to **tighten security** a bit. Also, it goes the extra mile and **unzips the downloaded reports**.

## Why?

### Once upon a time, there was autoingestion …
In the past, Apple has provided a tool called `autoingest` for automated retrieving of sales reports from iTunes Connect. While this tool worked quite reliably, it needed a full blown Java Runtime Environment installed. 

### … nowadays, it's all about Reporter
Apple will cut off autoingestion by the end of November 2016. It already has been replaced by a new and a bit more streamlined tool called `Reporter`. Unfortunately, `Reporter` is based on Java, too. It also suffers from a minor but annoying security threat as it needs to read iTunes Connect login credentials from a cleartext file.

### Java really is a sledge hammer to crack this nut
There really is no compelling reason to employ a Java tool with its somewhat heavyweight dependency on JRE in order to download a few reports from iTunes Connect. Apart from the Apple backend engineering staff really being into Java, apparently. Also, storing passwords in cleartext isn't state of the art anymore.

**iTC Reporter** (this Python script), on the other hand, solves both problems. It is written in pure Python and doesn't need Java or any external dependencies to function. Also, it can optionally read the iTC login password from the OS X Keychain (though it generally is still advisable to use an extra Apple ID specifically created for retrieving reports!).

## How?

The argument names and values of this script have mostly been chosen to be consistent with [Apple's documentation for Reporter](https://help.apple.com/itc/appsreporterguide/). An introduction will follow shortly. In the meantime, try `./reporter.py -h` for a quick usage summary: 
```text
usage: reporter.py [-h] [-a ACCOUNT] [-m {Normal,Robot.XML}] -u USERID
                   (-p PASSWORD_KEYCHAIN_OBJECT | -P PASSWORD)
                   {getStatus,getAccounts,getVendors,getSalesReport,getFinancialReport,getVendorsAndRegions}
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
  -p PASSWORD_KEYCHAIN_OBJECT, --password-keychain-object PASSWORD_KEYCHAIN_OBJECT
                        name of the macOS Keychain object that holds the Apple
                        ID password (cannot be used together with -P)
  -P PASSWORD, --password PASSWORD
                        Apple ID password (cannot be used together with -p)

commands:
  Specify the task you want to be carried out (use -h after a command's name
  to get additional help for that command)

  {getStatus,getAccounts,getVendors,getSalesReport,getFinancialReport,getVendorsAndRegions}
    getStatus           check if iTunes Connect is available for queries
    getAccounts         fetch a list of accounts accessible to the Apple ID
                        given in -u
    getVendors          fetch a list of vendors accessible to the Apple ID
                        given in -u
    getSalesReport      download a sales report file for a specific date range
    getFinancialReport  download a financial report file for a specific region
                        and fiscal period
    getVendorsAndRegions
                        fetch a list of financial reports you can download by
                        vendor number and region
```

Here is an example for retrieving the daily sales report for a specific account and vendor number while fetching the Apple ID's password from the OS X Keychain:

```sh
./reporter.py -u your@apple-id.com -p "Keychain Object: iTC Password" --account 2821955 getSalesReport 85442109 Daily 20160818
```

## TODO
There is currently no support for retrieving Newsstand-related reports, but I wonder if anybody using this script would really need it.

## Obligatory disclaimer

There is absolutely no warranty. I do not guarantee in any way that this tool works as intended or is fully compatible with Apple's official `Reporter` tool.

## Pull Requests
Neither English nor Python are my native language – corrective PRs (even for style only) are very welcome!
