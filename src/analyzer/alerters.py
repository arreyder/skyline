from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from smtplib import SMTP
import alerters
import settings


"""
Create any alerter you want here. The function will be invoked from trigger_alert.
Two arguments will be passed, both of them tuples: alert and metric.

alert: the tuple specified in your settings:
    alert[0]: The matched substring of the anomalous metric
    alert[1]: the name of the strategy being used to alert
    alert[2]: The timeout of the alert that was triggered
metric: information about the anomaly itself
    metric[0]: the anomalous value
    metric[1]: The full name of the anomalous metric
"""


def alert_smtp(alert, metric):

    # For backwards compatibility
    if '@' in alert[1]:
        sender = settings.ALERT_SENDER
        recipient = alert[1]
    else:
        sender = settings.SMTP_OPTS['sender']
        recipients = settings.SMTP_OPTS['recipients'][alert[0]]

    # Backwards compatibility
    if type(recipients) is str:
        recipients = [recipients]

    for recipient in recipients:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '[skyline alert] ' + metric[1]
        msg['From'] = sender
        msg['To'] = recipient
        link = '%s/render/?width=588&height=308&target=%s' % (settings.GRAPHITE_HOST, metric[1])
        body = 'Anomalous value: %s <br> Next alert in: %s seconds <a href="%s"><img src="%s"/></a>' % (metric[0], alert[2], link, link)
        msg.attach(MIMEText(body, 'html'))
        s = SMTP('127.0.0.1')
        s.sendmail(sender, recipient, msg.as_string())
        s.quit()


def alert_pagerduty(alert, metric):
    import pygerduty
    pager = pygerduty.PagerDuty(settings.PAGERDUTY_OPTS['subdomain'], settings.PAGERDUTY_OPTS['auth_token'])
    pager.trigger_incident(settings.PAGERDUTY_OPTS['key'], "Anomalous metric: %s (value: %s)" % (metric[1], metric[0]))


def alert_hipchat(alert, metric):
    import hipchat
    hipster = hipchat.HipChat(token=settings.HIPCHAT_OPTS['auth_token'])
    rooms = settings.HIPCHAT_OPTS['rooms'][alert[0]]
    link = '%s/render/?width=588&height=308&target=%s' % (settings.GRAPHITE_HOST, metric[1])

    for room in rooms:
        hipster.method('rooms/message', method='POST', parameters={'room_id': room, 'from': 'Skyline', 'color': settings.HIPCHAT_OPTS['color'], 'message': 'Anomaly: <a href="%s">%s</a> : %s' % (link, metric[1], metric[0])})

def alert_irccat(alert, metric):
    import socket
    HOST = settings.IRCCAT_OPTS['host']
    PORT = settings.IRCCAT_OPTS['port']
    CHANNEL = settings.IRCCAT_OPTS['channel']
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    message = '#ele-test skyline anomaly: https://graphite.cm.k1k.me/render?width=588&from=-1hour&until=-&height=308&target=%s' % (metric[1])
    s.send(message)
    s.close()

def alert_nsca(alert, metric):
    import subprocess
    HOST = settings.NSCA_OPTS['host']
    GRAPHITE_HOST_URL = settings.NSCA_OPTS['graphite_host_url']
    hname,branch,mname = metric[1].split(".",2)
    link = '%s/render?from=-1hour&target=%s' % (graphite_host_url, metric[1])
    message = '%s,%s,1,Telescope Rate Change Detected:%s\n' % (hname, mname, link)
    p = subprocess.Popen(['send_nsca','-H', HOST, '-to', '30', '-c', '/etc/send_nsca.cfg','-d', ','],stdin=subprocess.PIPE)
    p.communicate(input = message)


def trigger_alert(alert, metric):

    if '@' in alert[1]:
        strategy = 'alert_smtp'
    else:
        strategy = 'alert_' + alert[1]

    getattr(alerters, strategy)(alert, metric)
