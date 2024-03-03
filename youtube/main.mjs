#!/usr/bin/env node

import { JSDOM as Jsdom } from 'jsdom';
import jquery from 'jquery';

const base_url = 'https://www.apkmirror.com/apk/google-inc/youtube';
const version = process.argv[2].replace('.','-');

let $;
let debug = process.stdout.isTTY
  ? (msg) => { process.stdout.write(msg) }
  : () => { };

// selection page
const selection_url = `${base_url}/youtube-${version}-release`;
const selection_dom = await Jsdom.fromURL(selection_url);

debug(`visiting and parsing the selection page @${selection_url}\n`);

// download page
$ = jquery(selection_dom.window);
const download_url = $('.table span.apkm-badge:contains(APK)').parent().find('a')[0].href;
const download_dom = await Jsdom.fromURL(download_url);

debug('extracting the download page url from the anchor element that share a parent with a span that contain the text "APK"\n');
debug(`visiting and parsing the download page @${download_url}\n`);

// redirect page
$ = jquery(download_dom.window);
const redirect_url = $('.accent_bg.btn.btn-flat.downloadButton')
  .prop('href');
const redirect_dom = await Jsdom.fromURL(redirect_url);

debug('extracting the redirect page url from the download button\n');
debug(`visiting and parsing the redirect page @${redirect_url}\n`);

// direct download url
$ = jquery(redirect_dom.window);

debug('extract the direct download url from the href of the "here" link\n');
process.stdout.write($('a:contains(here)').prop('href'))
