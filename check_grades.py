#!/usr/bin/env python

# based on https://github.com/BenDoan/Infinite-Campus-Grade-Scraper

import cookielib
import mechanize
import config
from BeautifulSoup import BeautifulSoup
from xml.dom import minidom
import utils
import json

from colorama import Fore, Style
from colorama import init
init()

br = mechanize.Browser()


def main():
    print('setting up...')
    setup()
    print('logging in...')
    login()
    print('getting grades...')
    print '\n' * 2

    grades = {}

    class_links = get_class_links()

    for classname in class_links:
        for link in class_links[classname]:
            page = br.open(get_base_url() + link)

            soup = BeautifulSoup(page)
            # print soup

            grade_boxes = str(soup.findAll('td', {'class': 'gridInProgressGrade'}))
            assignment_boxes = soup.findAll('tr', {'class': 'gridCellNormal'})

            if grade_boxes:
                pos = grade_boxes.find("grayText")
                grade = grade_boxes[pos+10:pos+15]

            grades[classname] = {}
            grades[classname]['grade'] = grade
            grades[classname]['sections'] = {}

            current_section = None

            rows = soup.findAll(
                ['tr', 'td'], {'class': ['gridCellNormal', 'gridH2Top']})
            for row in rows:
                if row.name == 'td':
                    text = row.text
                    text = text.replace('&amp;', '&')
                    text = text.replace('&nbsp;', ' ')
                    if '(weight: ' in text:
                        section_name, weight = text[:-1].split('(weight: ')
                    else:
                        section_name, weight = text, '100'

                    grades[classname]['sections'][section_name] = {}
                    grades[classname]['sections'][section_name]['weight'] = weight
                    grades[classname]['sections'][section_name]['assignments'] = []
                    current_section = section_name
                    continue

                if row.find('a') is not None:
                    columns = row.findAll('td')

                    grades[classname]['sections'][current_section]['assignments'].append({
                        'assignment': columns.pop(0).text,
                        'due': columns.pop(0).text,
                        'assigned': columns.pop(0).text,
                        'multiplier': columns.pop(0).text,
                        'out of': columns.pop(0).text,
                        'score': columns.pop(0).text,
                        '%': columns.pop(0).text.replace('&nbsp;', ''),
                    })

    with open('grades_db.json', 'w+') as db:
        db.write(json.dumps(grades))
    display(grades)


def get_class_links():
    output = {}
    page = br.open(get_schedule_page_url())
    soup = BeautifulSoup(page)
    cell = soup.findAll('td')[-1]
    for cell in soup.findAll('td'):
        if cell.has_key('class') and cell['class'] == 'scheduleBody':
            link = cell.find('a')
            if link is not None:
                classname = ' '.join(link.find('b').text.split(' ')[1:])
                output[classname] = output[classname] if classname in output else []
                output[classname].append(link['href'])

    return output


def setup():
    """general setup commands"""
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    # User-Agent
    br.addheaders = [
        ('User-agent',
         'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]


def login():
    """Logs in to the Infinite Campus at the
    address specified in the config
    """
    br.open(config.login_url)
    br.select_form(nr=0)  # select the first form
    br.form['username'] = config.username
    br.form['password'] = config.password
    br.submit()


def get_base_url():
    """returns the site's base url, taken from the login page url"""
    return config.login_url.split("/campus")[0] + '/campus/'


def get_schedule_page_url():
    """returns the url of the schedule page"""
    school_data = br.open(get_base_url(
    ) + 'portal/portalOutlineWrapper.xsl?x=portal.PortalOutline&contentType=text/xml&lang=en')
    dom = minidom.parse(school_data)

    node = dom.getElementsByTagName('Student')[0]
    person_id = node.getAttribute('personID')
    first_name = node.getAttribute('firstName')
    last_name = node.getAttribute('lastName')

    node = dom.getElementsByTagName('Calendar')[0]
    school_id = node.getAttribute('schoolID')

    node = dom.getElementsByTagName('ScheduleStructure')[0]
    calendar_id = node.getAttribute('calendarID')
    structure_id = node.getAttribute('structureID')
    calendar_name = node.getAttribute('calendarName')

    url = 'portal/portal.xsl?x=portal.PortalOutline&lang=en'
    url += '&personID=' + person_id
    url += '&studentFirstName=' + first_name
    url += '&lastName=' + last_name
    url += '&firstName=' + first_name
    url += '&schoolID=' + school_id
    url += '&calendarID=' + calendar_id
    url += '&structureID=' + structure_id
    url += '&calendarName=' + calendar_name
    url += '&mode=schedule&x=portal.PortalSchedule&x=resource.PortalOptions'

    return utils.url_fix(get_base_url() + url)

def display(grades):

    headers = []
    spacing_formats = []
    color_formats = []

    headers.append('%')
    spacing_formats.append('{: <7}')
    color_formats.append('\033[0;32m' + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('assignment')
    spacing_formats.append('{: <50}')
    color_formats.append('\033[0;33m' + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('multiplier')
    spacing_formats.append('{: <12}')
    color_formats.append(
        Style.DIM + '\033[2;34m' + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('score')
    spacing_formats.append('{: <8}')
    color_formats.append(Fore.MAGENTA + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('out of')
    spacing_formats.append('{: <8}')
    color_formats.append(Fore.MAGENTA + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('due')
    spacing_formats.append('{: <11}')
    color_formats.append(Style.DIM + '{}' + Style.RESET_ALL + Fore.RESET)

    headers.append('assigned')
    spacing_formats.append('{: <11}')
    color_formats.append(Style.DIM + '{}' + Style.RESET_ALL + Fore.RESET)

    for class_name in grades:
        class_ = grades[class_name]
        # teacher = class_['teacher']
        grade = class_['grade']

        print '\033[4;36m' + class_name + Fore.RESET + Style.RESET_ALL
        # print '\033[2;4;36m' + teacher + Fore.RESET + Style.RESET_ALL
        if grade:
            print '\033[34m' + str(grade) + Fore.RESET + Style.RESET_ALL
        print ''

        if grade is 'None':
            print '\n' * 2

            continue

        print Style.BRIGHT + ' '.join(spacing_formats).format(*headers) + Style.RESET_ALL
        print ''

        for section_name in class_['sections']:
            section = class_['sections'][section_name]

            print ('\033[4;31m' + section_name +
                   Style.RESET_ALL).ljust(60) + ' - ' + section['weight'] + '%'

            for assignment in section['assignments']:
                data_columns = assignment

                data_values = [data_columns[key] for key in headers]

                for value, color_format, spacing_format in zip(data_values,
                                                               spacing_formats,
                                                               color_formats):
                    print spacing_format.format(color_format.format(value)),

                print ''
            print ''

        print '\n' * 2

if __name__ == '__main__':
    main()
