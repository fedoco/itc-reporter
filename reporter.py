#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse, urllib, urllib2, json, zlib, datetime, keychain

VERSION = '1.0'
ENDPOINT_SALES = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
ENDPOINT_FINANCE = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'


class Credentials:
    def __init__(self, account_number, user_id, password, mode):
        self.account_number = account_number
        self.user_id = user_id
        self.password = password
        self.mode = mode

class ITCReporter:

    def __init__(self, credentials):
        self.credentials = credentials

    def get_vendors(self):
        command = 'Sales.getVendors'
        request = APIClient.post_request(ENDPOINT_SALES, self.credentials, command)
        return ITCReporter.get_content(request)

    def get_status(self, service):
        command = service + '.getStatus'
        endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
        request = APIClient.post_request(endpoint, self.credentials, command)
        return ITCReporter.get_content(request)

    def get_accounts(self, service):
        command = service + '.getAccounts'
        endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
        request = APIClient.post_request(endpoint, self.credentials, command)
        return ITCReporter.get_content(request)

    def get_sales_report(self, vendor, report_type='Sales', report_subtype='Summary', date_type='Daily',
                         date=datetime.date.today()):
        params = ','.join([vendor, report_type, report_subtype, date_type, date.strftime("%Y%m%d")])
        command = 'Sales.getReport, ' + params
        request = APIClient.post_request(ENDPOINT_SALES, self.credentials, command)
        return ITCReporter.get_content(request)

    def get_financial_report(self, vendor, region_code, fiscal_year, fiscal_period):
        command = 'Finance.getReport, {0},{1},Financial,{2},{3}'.format(vendor, region_code, fiscal_year, fiscal_period)
        request = APIClient.post_request(ENDPOINT_FINANCE, self.credentials, command)
        return ITCReporter.get_content(request)

    def get_vendor_and_regions(self):
        command = 'Finance.getVendorsAndRegions'
        request = APIClient.post_request(ENDPOINT_FINANCE, self.credentials, command)
        return ITCReporter.get_content(request)

    @staticmethod
    def get_content(result):
        """Output (and when necessary unzip) the result of the request to the screen or into a report file"""

        content, header = result

        # unpack content into the final report file if it is gzip compressed.
        if header.gettype() == 'application/a-gzip':
            content = zlib.decompress(content, 15 + 32)
            filename = header.dict['filename'][:-3] or 'report.txt'
            report_file = open(filename, 'w')
            report_file.write(content)
            report_file.close()
            return content
        else:
            return content


class APIClient:

    @staticmethod
    def post_request(endpoint, credentials, command):
        """Execute the HTTP POST request"""
        print(command)
        command = "[p=Reporter.properties, %s]" % command
        request_data = APIClient.build_json_request_string(credentials, command)
        request = urllib2.Request(endpoint, request_data)
        request.add_header('Accept', 'text/html,image/gif,image/jpeg; q=.2, */*; q=.2')

        try:
            response = urllib2.urlopen(request)
            content = response.read()
            header = response.info()

            return content, header
        except urllib2.HTTPError, e:
            if e.code == 400 or e.code == 401 or e.code == 403 or e.code == 404:
                # for these error codes, the body always contains an error message
                raise ValueError(e.read())
            else:
                raise ValueError("HTTP Error %s. Did you choose reasonable query arguments?" % str(e.code))

    @staticmethod
    def build_json_request_string(credentials, query):
        """Build a JSON string from the urlquoted credentials and the actual query input"""

        request_data = dict(userid=credentials.user_id, password=credentials.password, version=VERSION, mode=credentials.mode, queryInput=query)
        request_data.update(account=credentials.account_number)  # empty account info would result in error 404

        request = {k: urllib.quote_plus(v) for k, v in request_data.items()}
        request = json.dumps(request)

        return 'jsonRequest=' + request


# command line arguments

#
# def parse_arguments():
#     """Build and parse the command line arguments"""
#
#     parser = argparse.ArgumentParser(
#         description="Reporting tool for querying Sales- and Financial Reports from iTunes Connect")
#
#     # (most of the time) optional arguments
#     parser.add_argument('-a', '--account', type=int,
#                         help="account number (needed if your Apple ID has access to multiple accounts; for a list of your account numbers, use the 'getAccounts' command)")
#     parser.add_argument('-m', '--mode', choices=['Normal', 'Robot.XML'], default='Normal',
#                         help="output format: plain text or XML (defaults to '%(default)s')")
#
#     # always required arguments
#     required_args = parser.add_argument_group("required arguments")
#     required_args.add_argument('-u', '--userid', required=True, help="Apple ID for use with iTunes Connect")
#     mutex_group = required_args.add_mutually_exclusive_group(required=True)
#     mutex_group.add_argument('-p', '--password-keychain-item',
#                              help="name of the macOS Keychain item that holds the Apple ID password (cannot be used together with -P)")
#     mutex_group.add_argument('-P', '--password', help="Apple ID password (cannot be used together with -p)")
#
#     # commands
#     subparsers = parser.add_subparsers(dest='command', title='commands',
#                                        description="Specify the task you want to be carried out (use -h after a command's name to get additional help for that command)")
#     parser_1 = subparsers.add_parser('getStatus', help="check if iTunes Connect is available for queries")
#     parser_1.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")
#
#     parser_2 = subparsers.add_parser('getAccounts',
#                                      help="fetch a list of accounts accessible to the Apple ID given in -u")
#     parser_2.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")
#
#     parser_3 = subparsers.add_parser('getVendors',
#                                      help="fetch a list of vendors accessible to the Apple ID given in -u")
#
#     parser_4 = subparsers.add_parser('getSalesReport', help="download a sales report file for a specific date range")
#     parser_4.add_argument('vendor', type=int,
#                           help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
#     parser_4.add_argument('report_type',
#                           choices=['Sales', 'Newsstand', 'Pre-order', 'Cloud', 'Event', 'Customer', 'Content',
#                                    'Station', 'Control', 'amEvent', 'amContent', 'amControl', 'amStreams',
#                                    'Subscription', 'SubscriptionEvent'], help="Report type")
#     parser_4.add_argument('report_subtype',
#                           choices=['Summary', 'Detailed', 'Opt-In'], default="Summary", help="Report subtype")
#     parser_4.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'],
#                           help="length of time covered by the report")
#     parser_4.add_argument('date',
#                           default=datetime.date.today().strftime("%Y%m%d"),
#                           help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
#
#     parser_5 = subparsers.add_parser('getFinancialReport',
#                                      help="download a financial report file for a specific region and fiscal period")
#     parser_5.add_argument('vendor', type=int,
#                           help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
#     parser_5.add_argument('regioncode',
#                           help="two-character code of country of the report to download (for a list of country codes by vendor number, use the 'getVendorsAndRegions' command)")
#     parser_5.add_argument('fiscalyear',
#                           help="four-digit year of the report to download (year is specific to Apple’s fiscal calendar)")
#     parser_5.add_argument('fiscalperiod',
#                           help="period in fiscal year for the report to download (1-12; period is specific to Apple’s fiscal calendar)")
#
#     parser_6 = subparsers.add_parser('getVendorsAndRegions',
#                                      help="fetch a list of financial reports you can download by vendor number and region")
#
#     return parser.parse_args()
#
#
# def validate_arguments(arguments):
#     """Do some additional checks on the passed arguments which argparse couldn't handle directly"""
#
#     if arguments.password_keychain_item:
#         try:
#             keychain.find_generic_password(None, arguments.password_keychain_item, '')
#         except:
#             raise ValueError(
#                 "Error: Could not find an item named '{0}' in the default Keychain".format(arguments.password_keychain_item))
#
#     if not arguments.account and (
#                 arguments.command == 'getVendorsAndRegions' or arguments.command == 'getVendors' or arguments.command == 'getFinancialReport'):
#         raise ValueError("Error: Argument -a/--account is needed for command '%s'" % arguments.command)
#
#     if hasattr(arguments, 'fiscalyear'):
#         try:
#             datetime.datetime.strptime(arguments.fiscalyear, "%Y")
#         except:
#             raise ValueError("Error: Fiscal year must be specified as YYYY")
#
#     if hasattr(arguments, 'fiscalperiod'):
#         try:
#             if int(arguments.fiscalperiod) < 1 or int(arguments.fiscalperiod) > 12:
#                 raise Exception
#         except:
#             raise ValueError("Error: Fiscal period must be a value between 1 and 12")
#
#     if hasattr(arguments, 'datetype'):
#         date_format = '%Y%m%d'
#         error = "Date must be specified as YYYYMMDD for daily reports"
#         if arguments.datetype == 'Weekly':
#             error = "Date must be specified as YYYYMMDD for weekly reports, where the day used is the Sunday that week ends"
#         if arguments.datetype == 'Monthly':
#             error = "Date must be specified as YYYYMM for monthly reports"
#             date_format = '%Y%m'
#         if arguments.datetype == 'Yearly':
#             error = "Date must be specified as YYYY for yearly reports"
#             date_format = '%Y'
#         try:
#             datetime.datetime.strptime(arguments.date, date_format)
#         except:
#             raise ValueError("Error: " + error)
#
#
# # main
#
# if __name__ == '__main__':
#     args = parse_arguments()
#
#     try:
#         validate_arguments(args)
#     except ValueError, e:
#         print e
#         exit(-1)
#
#     password = keychain.find_generic_password(None, args.password_keychain_item,
#                                               '') if args.password_keychain_item else args.password
#
#     credentials = (args.userid, password, str(args.account), args.mode)
#
#     try:
#         if args.command == 'getStatus':
#             get_status(credentials, args.service)
#         elif args.command == 'getAccounts':
#             get_accounts(credentials, args.service)
#         elif args.command == 'getVendors':
#             get_vendors(credentials)
#         elif args.command == 'getVendorsAndRegions':
#             get_vendor_and_regions(credentials)
#         elif args.command == 'getSalesReport':
#             get_sales_report(credentials, args.vendor, args.report_type, args.report_subtype, args.datetype, args.date)
#         elif args.command == 'getFinancialReport':
#             get_financial_report(credentials, args.vendor, args.regioncode, args.fiscalyear, args.fiscalperiod)
#     except ValueError, e:
#         print e
#         exit(-1)
#
#     exit(0)
