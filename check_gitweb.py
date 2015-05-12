#!/usr/bin/env python

import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import argparse
import sys

http = urllib3.PoolManager()

def main():
  parser = argparse.ArgumentParser(description='GitWeb diff')
  parser.add_argument("-s", dest="source", type=str, help="URL of master gitweb", required=True)
  parser.add_argument("-d", dest="destination", type=str, help="URL of slave gitweb", required=True)
  parser.add_argument("-w", dest="warn", default=0, type=int, help="Number of repos unsynced for critical")
  parser.add_argument("-c", dest="crit", default=10, type=int, help="Number of repos unsynced for critical")
  args = parser.parse_args()


  source_url = args.source
  destination_url = args.destination

  okey = 0

  gitdiffer = GitWebDiffer(source_url, destination_url)
  gitunsynced = gitdiffer.unsynced()

  msg = "OK: "

  if len(gitunsynced) > args.crit:
    okey = 2
    msg = "CRITICAL: " + str(len(gitunsynced)) + " repos not in sync! Those repos are:"
    for repo in gitunsynced:
      msg += " " + repo
  elif len(gitunsynced) > args.warn:
    okey = 1
    msg = "WARNING: " + str(len(gitunsynced)) + " repos not in sync! Those repos are:"
    for repo in gitunsynced:
      msg += " " + repo

  print(msg)
  sys.exit(okey)

class DictDiffer(object):
  """
  Calculate the difference between two dictionaries as:
  (1) items added
  (2) items removed
  (3) keys same in both but changed values
  (4) keys same in both and unchanged values
  """
  def __init__(self, current_dict, past_dict):
    self.current_dict, self.past_dict = current_dict, past_dict
    self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
    self.intersect = self.set_current.intersection(self.set_past)
  def added(self):
    return self.set_current - self.intersect 
  def removed(self):
    return self.set_past - self.intersect 
  def changed(self):
    return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
  def unchanged(self):
    return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

class GitWebDiffer:
  def __init__(self, master_url, slave_url):
    self.master_url = master_url
    self.slave_url = slave_url
    master_html = BeautifulSoup(http.request('GET', self.master_url).data)
    slave_html = BeautifulSoup(http.request('GET', self.slave_url).data)
    self.master_dict = self.__parse_project_list_dict(master_html)
    self.slave_dict = self.__parse_project_list_dict(slave_html)
    self.diff = self.__diff()

  def missing(self):
    missing = self.diff.added()
    missing_dict = {}
    for url in missing:
      last_change = self.__parse_get_last_change(BeautifulSoup(http.request('GET', self.master_url + "/?p=" + url).data))
      missing_dict[url]=last_change
    return missing_dict;

  def unsynced(self):
    unsynced = self.diff.changed()
    unsynced_dict = {}
    for url in unsynced:
      change_master = self.__parse_get_last_change(BeautifulSoup(http.request('GET', self.master_url + "/?p=" + url).data))
      change_slave = self.__parse_get_last_change(BeautifulSoup(http.request('GET', self.slave_url + "/?p=" + url).data))
      unsynced_dict[url] = change_master - change_slave
    return unsynced_dict

  def __diff(self):
    return DictDiffer(self.master_dict, self.slave_dict)

  def __parse_project_list_dict(self, html):
    tr_dict = {}
    for row in html.find('table', { 'class' : 'project_list' }).find_all('tr'):
      url=''
      age=''
      for index, td in enumerate(row.find_all('td')):
        if index==3:
          age=td.get_text()
        if index==0:
          url=td.get_text()
      tr_dict[url]=age
    return tr_dict

  def __parse_get_last_change(self, html):
    if html.find('td', text='last change') != None:
      return datetime.strptime(html.find('td', text='last change').nextSibling.get_text(), "%a, %d %b %Y %H:%M:%S %z")
    else:
      return datetime.now()

if __name__=='__main__':
    main()
