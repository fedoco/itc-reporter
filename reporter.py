#!/usr/bin/python
# -*- coding: utf-8 -*-

# Reporting tool for querying Sales- and Financial Reports from iTunes Connect
#
# This script mimics the official iTunes Connect Reporter by Apple which is used
# to automatically retrieve Sales- and Financial Reports for your App Store sales.
# It is written in pure Python and doesn’t need a Java runtime installation.
# Opposed to Apple’s tool, it can fetch iTunes Connect login credentials from the
# macOS Keychain in order to tighten security a bit. Also, it goes the extra mile
# and unzips the downloaded reports.
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

import argparse, urllib, urllib2, json, zlib, datetime, keychain

VERSION = '1.0'
ENDPOINT_SALES = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
ENDPOINT_FINANCE = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'

# queries

def get_vendors(credentials):
    command = 'Sales.getVendors'
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_status(credentials, service):
    command = service + '.getStatus'
    endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, credentials, command))

def get_accounts(credentials, service):
    command = service + '.getAccounts'
    endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, credentials, command))

def get_sales_report(credentials, vendor, datetype, date):
    command = 'Sales.getReport, {0},Sales,Summary,{1},{2}'.format(vendor, datetype, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_financial_report(credentials, vendor, regioncode, fiscalyear, fiscalperiod):
    command = 'Finance.getReport, {0},{1},Financial,{2},{3}'.format(vendor, regioncode, fiscalyear, fiscalperiod)
    output_result(post_request(ENDPOINT_FINANCE, credentials, command))

def get_vendor_and_regions(credentials):
    command = 'Finance.getVendorsAndRegions'
    output_result(post_request(ENDPOINT_FINANCE, credentials, command))

# HTTP request

def build_json_request_string(credentials, query):
    """Build a JSON string from the urlquoted credentials and the actual query input"""

    userid, password, account, mode = credentials

    request_data = dict(userid=userid, password=password, version=VERSION, mode=mode, queryInput=query)
    if account: request_data.update(account=account) # empty account info would result in error 404 

    request = {k: urllib.quote_plus(v) for k, v in request_data.items()}
    request = json.dumps(request)

    return 'jsonRequest=' + request

def post_request(endpoint, credentials, command):
    """Execute the HTTP POST request"""

    command = "[p=Reporter.properties, %s]" % command
    request_data = build_json_request_string(credentials, command)
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

def output_result(result):
    """Output (and when necessary unzip) the result of the request to the screen or into a report file"""

    content, header = result

    # unpack content into the final report file if it is gzip compressed.
    if header.gettype() == 'application/a-gzip':
        content = zlib.decompress(content, 15 + 32)
        filename = header.dict['filename'][:-3] or 'report.txt'
        file = open(filename, 'w')
        file.write(content)
        file.close()
        print header.dict['downloadmsg'].replace('.txt.gz', '.txt')
    else:
        print content

# command line arguments

def parse_arguments():
    """Build and parse the command line arguments"""

    parser = argparse.ArgumentParser(description="Reporting tool for querying Sales- and Financial Reports from iTunes Connect")

    # (most of the time) optional arguments
    parser.add_argument('-a', '--account', type=int, help="account number (needed if your Apple ID has access to multiple accounts; for a list of your account numbers, use the 'getAccounts' command)")
    parser.add_argument('-m', '--mode', choices=['Normal', 'Robot.XML'], default='Normal', help="output format: plain text or XML (defaults to '%(default)s')")

    # always required arguments
    required_args = parser.add_argument_group("required arguments")
    required_args.add_argument('-u', '--userid', required=True, help="Apple ID for use with iTunes Connect")
    mutex_group = required_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-p', '--password-keychain-item', help="name of the macOS Keychain item that holds the Apple ID password (cannot be used together with -P)")
    mutex_group.add_argument('-P', '--password', help="Apple ID password (cannot be used together with -p)")
    
    # commands
    subparsers = parser.add_subparsers(dest='command', title='commands', description="Specify the task you want to be carried out (use -h after a command's name to get additional help for that command)")
    parser_1 = subparsers.add_parser('getStatus', help="check if iTunes Connect is available for queries")
    parser_1.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")

    parser_2 = subparsers.add_parser('getAccounts', help="fetch a list of accounts accessible to the Apple ID given in -u")
    parser_2.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")

    parser_3 = subparsers.add_parser('getVendors', help="fetch a list of vendors accessible to the Apple ID given in -u")

    parser_4 = subparsers.add_parser('getSalesReport', help="download a sales report file for a specific date range")
    parser_4.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_4.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_4.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")

    parser_5 = subparsers.add_parser('getFinancialReport', help="download a financial report file for a specific region and fiscal period")
    parser_5.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_5.add_argument('regioncode', help="two-character code of country of the report to download (for a list of country codes by vendor number, use the 'getVendorsAndRegions' command)")
    parser_5.add_argument('fiscalyear', help="four-digit year of the report to download (year is specific to Apple’s fiscal calendar)") 
    parser_5.add_argument('fiscalperiod', help="period in fiscal year for the report to download (1-12; period is specific to Apple’s fiscal calendar)")

    parser_6 = subparsers.add_parser('getVendorsAndRegions', help="fetch a list of financial reports you can download by vendor number and region")

    return parser.parse_args()

def validate_arguments(args):
    """Do some additional checks on the passed arguments which argparse couldn't handle directly"""

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
      validate_arguments(args)
    except ValueError, e:
      print e
      exit(-1)

    password = keychain.find_generic_password(None, args.password_keychain_item, '') if args.password_keychain_item else args.password

    credentials = (args.userid, password, str(args.account), args.mode)

    try:
      if args.command == 'getStatus':
          get_status(credentials, args.service)
      elif args.command == 'getAccounts':
          get_accounts(credentials, args.service)
      elif args.command == 'getVendors':
          get_vendors(credentials)
      elif args.command == 'getVendorsAndRegions':
          get_vendor_and_regions(credentials)
      elif args.command == 'getSalesReport':
          get_sales_report(credentials, args.vendor, args.datetype, args.date)
      elif args.command == 'getFinancialReport':
          get_financial_report(credentials, args.vendor, args.regioncode, args.fiscalyear, args.fiscalperiod)
    except ValueError, e:
       print e
       exit(-1)

    exit(0)
