import os
import re
import datetime
import boto3
import jinja2

s3 = boto3.resource('s3')

def render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    fsl = jinja2.FileSystemLoader(path or './')
    output = jinja2.Environment(loader=fsl).get_template(filename).render(context)
    return output


def get_urls(strings_to_exclude):
    urls = []
    for item in s3.Bucket('projects.jsonline.com').objects.all():
        url = item.key
        if url.endswith('.html'):
            if not any(excludes in url for excludes in strings_to_exclude):
                data = get_url_metadata(url)
                urls.append(data)
    return urls


def get_url_metadata(url):
    file = s3.Object('projects.jsonline.com', url).get()
    contents = file['Body'].read()
    
    headline_regex = re.compile(r'<meta\s+name\=["\']mjs:headline["\']\s*content\=["\'](.*?)["\']\s*\/?>')
    try:
        headline = re.search(headline_regex, contents).group(1).decode('utf-8', 'replace')
    except:
        headline = ''
    
    dateline_regex = re.compile(r'<meta\s+name\=["\']mjs:dateline["\']\s*content\=["\'](.*?)["\']\s*\/?>')
    try:
        dateline = re.search(dateline_regex, contents).group(1)
        d = dateline.split('-')
        pubdate = datetime.date(int(d[0]), int(d[1]), int(d[2]))
    except:
        pubdate = datetime.date(2016, 6, 1) # start of projects.jsonline.com
    
    series_regex = re.compile(r'<meta\s+name\=["\']mjs:series["\']\s*content\=["\'](.*?)["\']\s*\/?>')
    try:
        series = re.search(series_regex, contents).group(1).decode('utf-8', 'replace')
    except:
        series = ''
    
    print url
    
    return {
        'link': url,
        'headline': headline,
        'dateline': pubdate,
        'series': series
    }


def group_links(links):
    groups = {
        'Non-Series': []
    }
    for link in links:
        series = link['series']
        if not series:
            groups['Non-Series'].append(link)
        elif series in groups:
            groups[series].append(link)
        else:
            groups[series] = [link]

    group_names = [k for k in groups]
    for key in group_names:
        vals = groups[key]
        groups[key] = sorted(vals, key=lambda v: v['dateline'], reverse=True)

    return groups


if __name__ == '__main__':

    excludes = ''
    with open('excludes.tsv', 'r') as f:
        excludes = filter(None, f.read().replace('\r', '').split('\n'))
    print "Excluding urls that contain: {}".format(', '.join(excludes))

    links = get_urls(excludes)
    print "Found {} pages on the projects server.".format(len(links))

    groups = group_links(links)
    print "Found {} series within the pages on the projects server.".format(len(groups))

    html = render('index-template.html', {'groups': groups})
    with open('index.html', 'w') as f:
        f.write(html)
