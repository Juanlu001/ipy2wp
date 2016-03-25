# -*- coding: utf-8 -*-
# Based on the work made by brave people and stored on
# https://github.com/ipython-contrib/IPython-notebook-extensions

import datetime
import argparse
from binascii import a2b_base64
import re
import os
import xmlrpc.client as xmlrpclib

import nbconvert as nbc
from traitlets.config import Config


def main():
    # Options
    parser = argparse.ArgumentParser(description='Publish ipynb to wp')
    parser.add_argument('--xmlrpc-url', help="The XML-RPC server/path url")
    parser.add_argument('--user', help="The wordpress user")
    parser.add_argument('--password', help="The wordpress user password")
    parser.add_argument('--nb', help="The path and notebook filename")
    parser.add_argument('--title', help="The title for the post in the site")
    parser.add_argument('--categories', nargs='+', help="A list of categories separated by space")
    parser.add_argument('--tags', nargs='+', help="A list of tags separated by spaces")
    parser.add_argument('--template', help="The template to be used, if none then basic is used")
    args = parser.parse_args()

    server = xmlrpclib.ServerProxy(args.xmlrpc_url)
    user = args.user
    password = args.password

    if args.template:
        tpl = args.template
        pathtpl, _ = os.path.split(os.path.abspath(__file__))
        pathtpl = os.path.join(pathtpl, 'templates', "{}.tpl".format(tpl))
        csstpl = os.path.join(pathtpl, 'templates', 'highlight.css')
        css_code = open(csstpl, 'r').read()
        post = """<style>{}</style>\n""".format(css_code)
    else:
        pathtpl = "basic"
        post = ""

    c = Config({'HTMLExporter': {'template_path': ['.', '/']}})
    post += nbc.export_html(nb=args.nb, template_file=pathtpl, config=c)[0]

    title = args.title

    if args.categories:
        categories = args.categories
    else:
        categories = ['Uncategorized']

    if args.tags:
        tags = args.tags
    else:
        tags = ''

    # Let's extract the images and upload to wp
    pat = re.compile('src="data:image/(.*?);base64,(.*?)"', re.DOTALL)
    count = 1
    postnew = post
    for ext, data in pat.findall(post):
        datab = a2b_base64(data)
        datab = xmlrpclib.Binary(datab)
        imgtitle = title.replace(' ', '_').replace('.', '-')
        out = {'name': imgtitle + str(count) + '.' + ext,
               'type': 'image/' + ext,
               'bits': datab,
               'overwrite': 'true'}
        count += 1
        image_id = server.wp.uploadFile("", user, password, out)
        urlimg = image_id['url']
        postnew = postnew.replace('data:image/' + ext + ';base64,' + data,
                                  urlimg)

    date_created = xmlrpclib.DateTime(datetime.datetime.now())
    status_published = 0
    wp_blogid = ""
    data = {'title': title,
            'description': postnew,
            'post_type': 'post',
            'dateCreated': date_created,
            'mt_allow_comments': 'open',
            'mt_allow_pings': 'open',
            'post_status': 'draft',
            'categories': categories,
            'mt_keywords': tags}
    server.metaWeblog.newPost(wp_blogid, user, password, data, status_published)

if __name__ == '__main__':
    main()
