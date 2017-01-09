from reporter import *

credentials = Credentials('87439801', 'Robot.XML')
reporter = ITCReporter(credentials)
yesterday = datetime.date.today() - datetime.timedelta(days=2)
report = reporter.get_sales_report('86167328', report_type='Subscription', date_type='Daily', date=yesterday)
print(report)
