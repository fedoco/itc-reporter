#!/usr/bin/python
# -*- coding: utf-8 -*-

# Reporting tool for querying Sales- and Financial Reports from iTunes Connect
#
# This script mimics the official iTunes Connect Reporter by Apple which is used
# to automatically retrieve Sales- and Financial Reports for your App Store sales.
# It is written in pure Python and doesn’t need a Java runtime installation.
# Opposed to Apple’s tool, it can fetch iTunes Connect login credentials from the
# macOS Keychain in order to tighten security a bit. Also, it goes the extra mile
# and unzips the downloaded reports if possible.
#
# Copyright (c) 2016 fedoco <fedoco@users.noreply.github.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys, argparse, urllib, urllib2, json, zlib, datetime
if sys.platform == 'darwin':
    import keychain

VERSION = '2.2'
ENDPOINT_SALES = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
ENDPOINT_FINANCE = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'

# iTC queries

def itc_get_vendors(args):
    command = 'Sales.getVendors'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_status(args):
    command = args.service + '.getStatus'
    endpoint = ENDPOINT_SALES if args.service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, get_credentials(args), command))

def itc_get_accounts(args):
    command = args.service + '.getAccounts'
    endpoint = ENDPOINT_SALES if args.service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, get_credentials(args), command))

def itc_get_vendor_and_regions(args):
    command = 'Finance.getVendorsAndRegions'
    output_result(post_request(ENDPOINT_FINANCE, get_credentials(args), command))

def itc_get_report_version(args):
    # service is limited to Sales for now because although documented it doesn't work for Finance
    command = 'Sales.getReportVersion, {0},{1}'.format(args.reporttype, args.reportsubtype)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_financial_report(args):
    command = 'Finance.getReport, {0},{1},Financial,{2},{3}'.format(args.vendor, args.regioncode, args.fiscalyear, args.fiscalperiod)
    output_result(post_request(ENDPOINT_FINANCE, get_credentials(args), command))

def itc_get_sales_report(args):
    command = 'Sales.getReport, {0},Sales,Summary,{1},{2}'.format(args.vendor, args.datetype, args.date)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_subscription_report(args):
    command = 'Sales.getReport, {0},Subscription,Summary,Daily,{1},{2}'.format(args.vendor, args.date, args.version)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_subscription_event_report(args):
    command = 'Sales.getReport, {0},SubscriptionEvent,Summary,Daily,{1},{2}'.format(args.vendor, args.date, args.version)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_subscriber_report(args):
    command = 'Sales.getReport, {0},Subscriber,Detailed,Daily,{1},{2}'.format(args.vendor, args.date, args.version)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_newsstand_report(args):
    command = 'Sales.getReport, {0},Newsstand,Detailed,{1},{2}'.format(args.vendor, args.datetype, args.date)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_get_opt_in_report(args):
    command = 'Sales.getReport, {0},Sales,Opt-In,Weekly,{1}'.format(args.vendor, args.date)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command), False) # do not attempt to unzip because it's password protected

def itc_get_pre_order_report(args):
    command = 'Sales.getReport, {0},Pre-Order,Summary,{1},{2}'.format(args.vendor, args.datetype, args.date)
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_view_token(args):
    command = 'Sales.viewToken'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

def itc_generate_token(args):
    command = 'Sales.generateToken'

    # generating a new token requires mirroring back a request id to the iTC server, so let's examine the response header...
    _, header = post_request(ENDPOINT_SALES, get_credentials(args), command)
    service_request_id = header.dict['service_request_id']

    # ...and post back the request id
    result = post_request(ENDPOINT_SALES, get_credentials(args), command, "&isExistingToken=Y&requestId=" + service_request_id)
    output_result(result)

    # optionally store the new token in Keychain upon success
    content, _ = result
    if content and args.update_keychain_item:
        for line in content.splitlines():
            if line.startswith("AccessToken:"):
                token = line[12:]
                keychain.set_generic_password(None, args.update_keychain_item, '', token)
                if not args.mode == 'Robot.XML': print "Keychain has been updated."
                break

def itc_delete_token(args):
    command = 'Sales.deleteToken'
    output_result(post_request(ENDPOINT_SALES, get_credentials(args), command))

# login credentials

def get_credentials(args):
    """Select iTunes Connect login credentials depending on given command line arguments"""

    # for most commands an iTunes Connect access token is needed - fetched either from the command line or from Keychain...
    access_token = keychain.find_generic_password(None, args.access_token_keychain_item, '') if args.access_token_keychain_item else args.access_token

    # ...but commands for access token manipulation need the plaintext password of the iTunes Connect account
    password = keychain.find_generic_password(None, args.password_keychain_item, '') if args.password_keychain_item else args.password 

    return (args.userid, access_token, password, str(args.account), args.mode)

# HTTP request

def build_json_request_string(credentials, query):
    """Build a JSON string from the urlquoted credentials and the actual query input"""

    userid, accessToken, password, account, mode = credentials

    request = dict(userid=userid, version=VERSION, mode=mode, queryInput=query)
    if account: request.update(account=account) # empty account info would result in error 404
    if accessToken: request.update(accesstoken=accessToken)
    if password: request.update(password=password)

    return urllib.urlencode(dict(jsonRequest=json.dumps(request)))

def post_request(endpoint, credentials, command, url_params = None):
    """Execute the HTTP POST request"""

    command = "[p=Reporter.properties, %s]" % command
    request_data = build_json_request_string(credentials, command)
    if url_params: request_data += url_params

    request = urllib2.Request(endpoint, request_data)
    request.add_header('Accept', 'text/html,image/gif,image/jpeg; q=.2, */*; q=.2')

    try:
        response = urllib2.urlopen(request)
        content = response.read()
        header = response.info()

        return (content, header)
    except urllib2.HTTPError, e:
        if e.code == 400 or e.code == 401 or e.code == 403 or e.code == 404:
            # for these error codes, the body always contains an error message
            raise ValueError(e.read())
        else:
            raise ValueError("HTTP Error %s. Did you choose reasonable query arguments?" % str(e.code))

def output_result(result, unzip = True):
    """Output (and when necessary unzip) the result of the request to the screen or into a report file"""

    content, header = result

    # unpack content into the final report file if it is gzip compressed.
    if header.gettype() == 'application/a-gzip':
        msg = header.dict['downloadmsg']
        filename = header.dict['filename'] or 'report.txt.gz'
        if unzip:
            msg = msg.replace('.txt.gz', '.txt')
            filename = filename[:-3]
            content = zlib.decompress(content, 15 + 32)
        file = open(filename, 'w')
        file.write(content)
        file.close()
        print msg
    else:
        print content

# command line arguments

def parse_arguments():
    """Build and parse the command line arguments"""

    parser_main = argparse.ArgumentParser(description="Reporting tool for querying Sales- and Financial Reports from iTunes Connect", epilog="For a detailed description of report types, see http://help.apple.com/itc/appssalesandtrends/#/itc37a18bcbf")

    # (most of the time) optional arguments
    parser_main.add_argument('-a', '--account', type=int, help="account number (needed if your Apple ID has access to multiple accounts; for a list of your account numbers, use the 'getAccounts' command)")
    parser_main.add_argument('-m', '--mode', choices=['Normal', 'Robot.XML'], default='Normal', help="output format: plain text or XML (defaults to '%(default)s')")

    # always required arguments
    required_args = parser_main.add_argument_group("required arguments")
    required_args.add_argument('-u', '--userid', required=True, help="Apple ID for use with iTunes Connect")

    # template for commands that require authentication with password
    parser_auth_password = argparse.ArgumentParser(add_help=False)
    parser_auth_password.set_defaults(access_token=None, access_token_keychain_item=None)
    auth_password_args = parser_auth_password.add_argument_group()
    mutex_group = auth_password_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-p', '--password-keychain-item', metavar="KEYCHAIN_ITEM", help='name of the macOS Keychain item that holds the Apple ID password (cannot be used together with -P)')
    mutex_group.add_argument('-P', '--password', help='Apple ID password (cannot be used together with -p)')

    # template for commands that require authentication with access token
    parser_auth_token = argparse.ArgumentParser(add_help=False)
    parser_auth_token.set_defaults(password=None, password_keychain_item=None)
    auth_token_args = parser_auth_token.add_argument_group()
    mutex_group = auth_token_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-t', '--access-token-keychain-item', metavar="KEYCHAIN_ITEM", help='name of the macOS Keychain item that holds the iTunes Connect access token (more secure alternative to -T)')
    mutex_group.add_argument('-T', '--access-token', help='iTunes Connect access token (can be obtained with the generateToken command or via iTunes Connect -> Sales & Trends -> Reports -> About Reports)')

    # commands
    subparsers = parser_main.add_subparsers(dest='command', title='commands', description="Specify the task you want to be carried out (use -h after a command's name to get additional help for that command)")

    parser_cmd = subparsers.add_parser('getStatus', help="check if iTunes Connect is available for queries", parents=[parser_auth_token])
    parser_cmd.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")
    parser_cmd.set_defaults(func=itc_get_status)

    parser_cmd = subparsers.add_parser('getAccounts', help="fetch a list of accounts accessible to the Apple ID given in -u", parents=[parser_auth_token])
    parser_cmd.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")
    parser_cmd.set_defaults(func=itc_get_accounts)

    parser_cmd = subparsers.add_parser('getVendors', help="fetch a list of vendors accessible to the Apple ID given in -u", parents=[parser_auth_token])
    parser_cmd.set_defaults(func=itc_get_vendors)

    parser_cmd = subparsers.add_parser('getVendorsAndRegions', help="fetch a list of financial reports you can download by vendor number and region", parents=[parser_auth_token])
    parser_cmd.set_defaults(func=itc_get_vendor_and_regions)

    parser_cmd = subparsers.add_parser('getReportVersion', help="query what is the latest available version of reports of a specific type and subtype", parents=[parser_auth_token])
    parser_cmd.add_argument('reporttype', choices=['Sales', 'Subscription', 'SubscriptionEvent', 'Subscriber', 'Newsstand', 'Pre-Order'])
    parser_cmd.add_argument('reportsubtype', choices=['Summary', 'Detailed', 'Opt-In'])
    parser_cmd.set_defaults(func=itc_get_report_version)

    parser_cmd = subparsers.add_parser('getFinancialReport', help="download a financial report file for a specific region and fiscal period", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('regioncode', help="two-character code of country of the report to download (for a list of country codes by vendor number, use the 'getVendorsAndRegions' command)")
    parser_cmd.add_argument('fiscalyear', help="four-digit year of the report to download (year is specific to Apple’s fiscal calendar)")
    parser_cmd.add_argument('fiscalperiod', help="period in fiscal year for the report to download (1-12; period is specific to Apple’s fiscal calendar)")
    parser_cmd.set_defaults(func=itc_get_financial_report)

    parser_cmd = subparsers.add_parser('getSalesReport', help="download a summary sales report file for a specific date range", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_cmd.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
    parser_cmd.set_defaults(func=itc_get_sales_report)

    parser_cmd = subparsers.add_parser('getSubscriptionReport', help="download a subscription report file for a specific day", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")
    parser_cmd.add_argument('-v', '--version', choices=['1_0', '1_1'], default='1_1', help="report format version to use (if omitted, the latest available version is used)")
    parser_cmd.set_defaults(func=itc_get_subscription_report)

    parser_cmd = subparsers.add_parser('getSubscriptionEventReport', help="download an aggregated subscriber activity report file for a specific day", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")
    parser_cmd.add_argument('-v', '--version', choices=['1_0', '1_1'], default='1_1', help="report format version to use (if omitted, the latest available version is used)")
    parser_cmd.set_defaults(func=itc_get_subscription_event_report)

    parser_cmd = subparsers.add_parser('getSubscriberReport', help="download a transaction-level subscriber activity report file for a specific day", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")
    parser_cmd.add_argument('-v', '--version', choices=['1_0', '1_1'], default='1_1', help="report format version to use (if omitted, the latest available version is used)")
    parser_cmd.set_defaults(func=itc_get_subscriber_report)

    parser_cmd = subparsers.add_parser('getNewsstandReport', help="download a magazines & newspapers report file for a specific date range", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('datetype', choices=['Daily', 'Weekly'], help="length of time covered by the report")
    parser_cmd.add_argument('date', help="specific time covered by the report (weekly reports, like daily reports, use YYYYMMDD, where the day used is the Sunday that week ends")
    parser_cmd.set_defaults(func=itc_get_newsstand_report)

    parser_cmd = subparsers.add_parser('getOptInReport', help="download contact information for customers who opt in to share their contact information with you", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")
    parser_cmd.set_defaults(func=itc_get_opt_in_report)

    parser_cmd = subparsers.add_parser('getPreOrderReport', help="download a summary report file of pre-ordered items for a specific date range", parents=[parser_auth_token])
    parser_cmd.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_cmd.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_cmd.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
    parser_cmd.set_defaults(func=itc_get_pre_order_report)

    parser_cmd = subparsers.add_parser('generateToken', help="generate a token for accessing iTunes Connect (expires after 180 days) and optionally store it in the macOS Keychain", parents=[parser_auth_password])
    parser_cmd.add_argument('--update-keychain-item', metavar="KEYCHAIN_ITEM", help='name of the macOS Keychain item in which the new access token should be stored in')
    parser_cmd.set_defaults(func=itc_generate_token)

    parser_cmd = subparsers.add_parser('viewToken', help="display current iTunes Connect access token and its expiration date", parents=[parser_auth_password])
    parser_cmd.set_defaults(func=itc_view_token)

    parser_cmd = subparsers.add_parser('deleteToken', help="delete an existing iTunes Connect access token", parents=[parser_auth_password])
    parser_cmd.set_defaults(func=itc_delete_token)

    args = parser_main.parse_args()

    try:
        validate_arguments(args)
    except ValueError, e:
        parser_main.error(e)

    return args

def validate_arguments(args):
    """Do some additional checks on the passed arguments which argparse couldn't handle directly"""

    if sys.platform != 'darwin' and (args.password_keychain_item or args.access_token_keychain_item):
        raise ValueError("Error: Keychain support is limited to macOS")

    if args.access_token_keychain_item:
        try:
            keychain.find_generic_password(None, args.access_token_keychain_item, '')
        except:
            raise ValueError("Error: Could not find an item named '{0}' in the default Keychain".format(args.access_token_keychain_item))

    if args.password_keychain_item:
        try:
            keychain.find_generic_password(None, args.password_keychain_item, '')
        except:
            raise ValueError("Error: Could not find an item named '{0}' in the default Keychain".format(args.password_keychain_item))

    if not args.account and (args.command == 'getVendorsAndRegions' or args.command == 'getVendors' or args.command == 'getFinancialReport'):
        raise ValueError("Error: Argument -a/--account is needed for command '%s'" % args.command)

    if hasattr(args, 'fiscalyear'):
        try:
            datetime.datetime.strptime(args.fiscalyear, "%Y")
        except:
            raise ValueError("Error: Fiscal year must be specified as YYYY")

    if hasattr(args, 'fiscalperiod'):
        try:
            if int(args.fiscalperiod) < 1 or int(args.fiscalperiod) > 12:
                raise Exception
        except:
            raise ValueError("Error: Fiscal period must be a value between 1 and 12")

    if hasattr(args, 'datetype'):
        format = '%Y%m%d'
        error = "Date must be specified as YYYYMMDD for daily reports"
        if args.datetype == 'Weekly':
            error = "Date must be specified as YYYYMMDD for weekly reports, where the day used is the Sunday that week ends"
        if args.datetype == 'Monthly':
            error = "Date must be specified as YYYYMM for monthly reports"
            format = '%Y%m'
        if args.datetype == 'Yearly':
            error = "Date must be specified as YYYY for yearly reports"
            format = '%Y'
        try:
            datetime.datetime.strptime(args.date, format)
        except:
            raise ValueError("Error: " + error)

# main

if __name__ == '__main__':
    args = parse_arguments()

    try:
        args.func(args)
    except ValueError, e:
        print e
        exit(-1)

    exit(0)
