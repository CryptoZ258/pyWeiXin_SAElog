# -*- coding: utf-8 -*-
import logging
import re
from hashlib import md5

from time import time
from datetime import datetime

from common import slugfy, time_from_now, cnnow, memcached, timestamp_to_datetime, safe_encode
from setting import *

try:
    from tornado import database
except:
    pass

##
##数据库配置信息
if debug:
    #已经在setting里设置了
    pass
else:
    import sae.const
    MYSQL_DB = sae.const.MYSQL_DB
    MYSQL_USER = sae.const.MYSQL_USER
    MYSQL_PASS = sae.const.MYSQL_PASS
    MYSQL_HOST_M = sae.const.MYSQL_HOST
    MYSQL_HOST_S = sae.const.MYSQL_HOST_S
    MYSQL_PORT = sae.const.MYSQL_PORT
    
#主数据库 进行Create,Update,Delete 操作
#从数据库 读取

##
HTML_REG = re.compile(r"""<[^>]+>""", re.I|re.M|re.S)

mdb = database.Connection("%s:%s"%(MYSQL_HOST_M,str(MYSQL_PORT)), MYSQL_DB,MYSQL_USER, MYSQL_PASS, max_idle_time = MAX_IDLE_TIME)
sdb = database.Connection("%s:%s"%(MYSQL_HOST_S,str(MYSQL_PORT)), MYSQL_DB,MYSQL_USER, MYSQL_PASS, max_idle_time = MAX_IDLE_TIME)

###
CODE_RE = re.compile(r"""\[code\](.+?)\[/code\]""",re.I|re.M|re.S)

def n2br(text):
    con = text.replace('>\n\n','>').replace('>\n','>')
    con = "<p>%s</p>"%('</p><p>'.join(con.split('\n\n')))
    return '<br/>'.join(con.split("\n"))    
    
def tran_content(text, code = False):
    if code:
        codetag = '[mycodeplace]'
        codes = CODE_RE.findall(text)
        for i in range(len(codes)):
            text = text.replace(codes[i],codetag)
        text = text.replace("[code]","").replace("[/code]","")
        
        text = n2br(text)
        
        a = text.split(codetag)
        b = []
        for i in range(len(a)):
            b.append(a[i])
            try:
                b.append('<pre><code>' + safe_encode(codes[i]) + '</code></pre>')
            except:
                pass
                        
        return ''.join(b)
    else:
        return n2br(text)

def post_list_format(posts):
    for obj in posts:
        obj.absolute_url = '%s/topic/%d/%s' % (BASE_URL, obj.id, slugfy(obj.title))
        obj.taglist = ', '.join(["""<a href="%s/tag/%s/" rel="tag">%s</a>"""%(BASE_URL, tag, tag) for tag in obj.tags.split(',')])
        
        if '<!--more-->' in obj.content:
            obj.shorten_content = obj.content.split('<!--more-->')[0]
        else:
            obj.shorten_content = HTML_REG.sub('',obj.content[:SHORTEN_CONTENT_WORDS])
        
        obj.add_time_fn = time_from_now(int(obj.add_time))
    return posts

def post_detail_formate(obj):
    if obj:
        slug = slugfy(obj.title)
        obj.slug = slug
        obj.absolute_url = '%s/topic/%d/%s' % (BASE_URL, obj.id, slug)
        obj.shorten_url = '%s/t/%s' % (BASE_URL, obj.id)
        if '[/code]' in obj.content:
            obj.highlight = True
        else:
            obj.highlight = False        
        obj.content = tran_content(obj.content, obj.highlight)
        obj.taglist = ', '.join(["""<a href="%s/tag/%s/" rel="tag">%s</a>"""%(BASE_URL, tag, tag) for tag in obj.tags.split(',')])
        obj.add_time_fn = time_from_now(int(obj.add_time))
        obj.last_modified = timestamp_to_datetime(obj.edit_time)
        obj.keywords = obj.tags
        obj.description = HTML_REG.sub('',obj.content[:DESCRIPTION_CUT_WORDS])
        #get prev and next obj
        obj.prev_obj = sdb.get('SELECT `id`,`title` FROM `sp_posts` WHERE `id` > %s LIMIT 1' % str(obj.id))
        if obj.prev_obj:
            obj.prev_obj.slug = slugfy(obj.prev_obj.title)
        obj.next_obj = sdb.get('SELECT `id`,`title` FROM `sp_posts` WHERE `id` < %s ORDER BY `id` DESC LIMIT 1' % str(obj.id))
        if obj.next_obj:
            obj.next_obj.slug = slugfy(obj.next_obj.title)
        #get relative obj base tags
        obj.relative = []
        if obj.tags:
            idlist = []
            getit = False
            for tag in obj.tags.split(','):
                tagobj = Tag.get_tag_by_name(tag)
                if tagobj and tagobj.content:
                    pids = tagobj.content.split(',')
                    for pid in pids:
                        if pid != str(obj.id) and pid not in idlist:
                            idlist.append(pid)
                            if len(idlist) >= RELATIVE_POST_NUM:
                                getit = True
                                break
                if getit:
                    break
            #
            if idlist:
                obj.relative = sdb.query('SELECT `id`,`title` FROM `sp_posts` WHERE `id` in(%s) LIMIT %s' % (','.join(idlist), str(len(idlist))))
                if obj.relative:
                    for robj in obj.relative:
                        robj.slug = slugfy(robj.title)
        #get comment
        obj.coms = []
        if obj.comment_num >0:
            if obj.comment_num >= EACH_PAGE_COMMENT_NUM:
                first_limit = EACH_PAGE_COMMENT_NUM
            else:
                first_limit = obj.comment_num
            obj.coms = Comment.get_post_page_comments_by_id( obj.id, 0, first_limit )
    return obj

def comment_format(objs):
    for obj in objs:
        obj.gravatar = 'http://www.gravatar.com/avatar/%s'%md5(obj.email).hexdigest()
        obj.add_time = time_from_now(int(obj.add_time))
        
        if obj.visible:
            obj.short_content = HTML_REG.sub('',obj.content[:RECENT_COMMENT_CUT_WORDS])
        else:
            obj.short_content = 'Your comment is awaiting moderation.'[:RECENT_COMMENT_CUT_WORDS]
        
        obj.content = obj.content.replace('\n','<br/>')
    return objs

###以下是各个数据表的操作

###########

class Article():
    def get_max_id(self):
        sdb._ensure_connected()
        maxobj = sdb.query("select max(id) as maxid from `sp_posts`")
        return str(maxobj[0]['maxid'])
    
    def get_last_post_add_time(self):
        sdb._ensure_connected()
        obj = sdb.get('SELECT `add_time` FROM `sp_posts` ORDER BY `id` DESC LIMIT 1')
        if obj:
            return datetime.fromtimestamp(obj.add_time)
        else:
            return datetime.utcnow() + timedelta(hours =+ 8)
    
    def count_all_post(self):
        sdb._ensure_connected()
        return sdb.query('SELECT COUNT(*) AS postnum FROM `sp_posts`')[0]['postnum']
    
    def get_all_article(self):
        sdb._ensure_connected()
        return post_list_format(sdb.query("SELECT * FROM `sp_posts` ORDER BY `id` DESC"))
    
    def get_post_for_homepage(self):
        sdb._ensure_connected()
        return post_list_format(sdb.query("SELECT * FROM `sp_posts` ORDER BY `id` DESC LIMIT %s" % str(EACH_PAGE_POST_NUM)))
    
    def get_page_posts(self, direction = 'next', page = 1 , base_id = '', limit = EACH_PAGE_POST_NUM):
        sdb._ensure_connected()
        if direction == 'next':
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` < %s ORDER BY `id` DESC LIMIT %s" % (str(base_id), str(EACH_PAGE_POST_NUM))))
        else:
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` > %s ORDER BY `id` ASC LIMIT %s" % (str(base_id), str(EACH_PAGE_POST_NUM))))
            
    def get_article_by_id_detail(self, id):
        sdb._ensure_connected()
        return post_detail_formate(sdb.get('SELECT * FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id)))
    
    # 新添加的用于关键字查询文章 by bibodeng 2013-05-07
    def get_article_by_keyword(self, keyword):
        sdb._ensure_connected()
        keyword_quote = '%'+ keyword +'%'
        return post_detail_formate(sdb.get('SELECT * FROM `sp_posts` WHERE `title` LIKE %s OR `tags` LIKE %s LIMIT 1' , str(keyword_quote), str(keyword_quote)))
        # 历尽千辛万苦，包括like，还有get与query之间的区别阿
        
    # 返回一个包含若干篇文章的数组 limit 5
    def get_articles_by_category(self, category):
        sdb._ensure_connected()
        article_list = sdb.query('SELECT * FROM `sp_posts` WHERE `category` = %s LIMIT 5', str(category))
        for i in range(len(article_list)):
            article_list[i] = post_detail_formate(article_list[i])
        return article_list
    # 最新文章
    def get_articles_by_latest(self):
        sdb._ensure_connected()
        article_list = sdb.query('SELECT * FROM `sp_posts` ORDER BY `id` DESC LIMIT 5')
        for i in range(len(article_list)):
            article_list[i] = post_detail_formate(article_list[i])
        return article_list
        
    def get_all_article_list(self):
        sdb._ensure_connected()
        article_list = sdb.query('SELECT id,title,category FROM `sp_posts` ORDER BY `id` DESC LIMIT 20')
        return article_list
        
    def get_article_by_id_simple(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT `id`,`title`,`comment_num`,`closecomment`,`password` FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id))
    
    def get_article_by_id_edit(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id))
        
    def add_new_article(self, params):
        query = "INSERT INTO `sp_posts` (`category`,`title`,`content`,`closecomment`,`tags`,`password`,`add_time`,`edit_time`) values(%s,%s,%s,%s,%s,%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['category'], params['title'], params['content'], params['closecomment'], params['tags'], params['password'], params['add_time'], params['edit_time'])
    
    def update_post_edit(self, params):
        query = "UPDATE `sp_posts` SET `category` = %s, `title` = %s, `content` = %s, `closecomment` = %s, `tags` = %s, `password` = %s, `edit_time` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['category'], params['title'], params['content'], params['closecomment'], params['tags'], params['password'], params['edit_time'], params['id'])
        ### update 返回不了 lastrowid，直接返回 post id
        return params['id']
            
    def update_post_comment(self, num = 1,id = ''):
        query = "UPDATE `sp_posts` SET `comment_num` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        return mdb.execute(query, num, id)
    
    def get_post_for_sitemap(self, ids=[]):
        sdb._ensure_connected()
        return sdb.query("SELECT `id`,`edit_time` FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(ids), str(len(ids))))
    
    def del_post_by_id(self, id = ''):
        if id:
            obj = self.get_article_by_id_simple(id)
            if obj:
                limit = obj.comment_num
                mdb._ensure_connected()
                mdb.execute("DELETE FROM `sp_posts` WHERE `id` = %s LIMIT 1", id)
                mdb.execute("DELETE FROM `sp_comments` WHERE `postid` = %s LIMIT %s", id, limit)
                

Article = Article()

class Comment():
    def del_comment_by_id(self, id):
        cobj = self.get_comment_by_id(id)
        postid = cobj.postid
        pobj = Article.get_article_by_id_edit(postid)
        
        mdb._ensure_connected()
        mdb.execute("DELETE FROM `sp_comments` WHERE `id` = %s LIMIT 1", id)
        if pobj:
            Article.update_post_comment( pobj.comment_num-1, postid)
        return
    
    def get_comment_by_id(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_comments` WHERE `id` = %s LIMIT 1' % str(id))
        
    def get_recent_comments(self, limit = RECENT_COMMENT_NUM):
        sdb._ensure_connected()
        return comment_format(sdb.query('SELECT * FROM `sp_comments` ORDER BY `id` DESC LIMIT %s' % str(limit)))
    
    def get_post_page_comments_by_id(self, postid = 0, min_comment_id = 0, limit = EACH_PAGE_COMMENT_NUM):
        
        if min_comment_id == 0:
            sdb._ensure_connected()
            return comment_format(sdb.query('SELECT * FROM `sp_comments` WHERE `postid`= %s ORDER BY `id` DESC LIMIT %s' % (str(postid), str(limit))))
        else:
            sdb._ensure_connected()
            return comment_format(sdb.query('SELECT * FROM `sp_comments` WHERE `postid`= %s AND `id` < %s ORDER BY `id` DESC LIMIT %s' % (str(postid), str(min_comment_id), str(limit))))
        
    def add_new_comment(self, params):
        query = "INSERT INTO `sp_comments` (`postid`,`author`,`email`,`url`,`visible`,`add_time`,`content`) values(%s,%s,%s,%s,%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['postid'], params['author'], params['email'], params['url'], params['visible'], params['add_time'], params['content'])
        
    def update_comment_edit(self, params):
        query = "UPDATE `sp_comments` SET `author` = %s, `email` = %s, `url` = %s, `visible` = %s, `content` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['author'], params['email'], params['url'], params['visible'], params['content'], params['id'])
        ### update 返回不了 lastrowid，直接返回 id
        return params['id']
    

Comment = Comment()

class Link():
    def get_all_links(self, limit = LINK_NUM):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_links` ORDER BY `displayorder` DESC LIMIT %s' % str(limit))
    
    def add_new_link(self, params):
        query = "INSERT INTO `sp_links` (`displayorder`,`name`,`url`) values(%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['displayorder'], params['name'], params['url'])
    
    def update_link_edit(self, params):
        query = "UPDATE `sp_links` SET `displayorder` = %s, `name` = %s, `url` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['displayorder'], params['name'], params['url'], params['id'])
    
    def del_link_by_id(self, id):
        mdb._ensure_connected()
        mdb.execute("DELETE FROM `sp_links` WHERE `id` = %s LIMIT 1", id)
        
    def get_link_by_id(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_links` WHERE `id` = %s LIMIT 1' % str(id))    

Link = Link()

class Category():
    def get_all_cat_name(self):
        sdb._ensure_connected()
        return sdb.query('SELECT `name`,`id_num` FROM `sp_category` ORDER BY `id` DESC')
        
    def get_all_cat(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_category` ORDER BY `id` DESC')
    
    def get_all_cat_id(self):
        sdb._ensure_connected()
        return sdb.query('SELECT `id` FROM `sp_category` ORDER BY `id` DESC')
    
    def get_cat_by_name(self, name = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)
            
    def get_all_post_num(self, name = ''):
        obj = self.get_cat_by_name(name)
        if obj and obj.content:
            return len(obj.content.split(','))
        else:
            return 0
        
    def get_cat_page_posts(self, name = '', page = 1, limit = EACH_PAGE_POST_NUM):
        obj = self.get_cat_by_name(name)
        if obj:
            page = int(page)
            idlist = obj.content.split(',')
            getids = idlist[limit*(page-1):limit*page]
            sdb._ensure_connected()
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(getids), str(len(getids)))))
        else:
            return []
            
    def add_postid_to_cat(self, name = '', postid = ''):
        mdb._ensure_connected()
        #因为 UPDATE 时无论有没有影响行数，都返回0，所以这里要多读一次（从主数据库读）
        obj = mdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)        
        
        if obj:
            query = "UPDATE `sp_category` SET `id_num` = `id_num` + 1, `content` =  concat(%s, `content`) WHERE `id` = %s LIMIT 1"
            mdb.execute(query, "%s,"%postid, obj.id)
        else:
            query = "INSERT INTO `sp_category` (`name`,`id_num`,`content`) values(%s,1,%s)"
            mdb.execute(query, name, postid)
    
    def remove_postid_from_cat(self, name = '', postid = ''):
        mdb._ensure_connected()
        obj = mdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)        
        if obj:
            idlist = obj.content.split(',')
            if postid in idlist:
                idlist.remove(postid)
                try:
                    idlist.remove('')
                except:
                    pass
                if len(idlist) == 0:
                    mdb.execute("DELETE FROM `sp_category` WHERE `id` = %s LIMIT 1", obj.id)
                else:
                    query = "UPDATE `sp_category` SET `id_num` = %s, `content` =  %s WHERE `id` = %s LIMIT 1"
                    mdb.execute(query, len(idlist), ','.join(idlist), obj.id)                
            else:
                pass
    
    def get_cat_by_id(self, id = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_category` WHERE `id` = %s LIMIT 1' % str(id))
    
    def get_sitemap_by_id(self, id=''):
        
        obj = self.get_cat_by_id(id)
        if not obj:
            return ''
        if not obj.content:
            return ''
        
        urlstr = """<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>\n """        
        urllist = []
        urllist.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        urllist.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        
        urllist.append(urlstr%( "%s/c/%s" % (BASE_URL, str(obj.id)), cnnow().strftime("%Y-%m-%dT%H:%M:%SZ"), 'daily', '0.8'))
        
        objs = Article.get_post_for_sitemap(obj.content.split(','))
        for p in objs:
            if p:
                urllist.append(urlstr%("%s/t/%s" % (BASE_URL, str(p.id)), timestamp_to_datetime(p.edit_time).strftime("%Y-%m-%dT%H:%M:%SZ"), 'weekly', '0.6'))
        
        urllist.append('</urlset>')
        return ''.join(urllist)

Category = Category()

class Tag():
    def get_all_tag_name(self):
        #for add/edit post
        sdb._ensure_connected()
        return sdb.query('SELECT `name` FROM `sp_tags` ORDER BY `id` DESC LIMIT %d' % HOT_TAGS_NUM)

    def get_all_tag(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_tags` ORDER BY `id` DESC LIMIT %d' % HOT_TAGS_NUM)
    
    def get_hot_tag_name(self):
        #for sider
        sdb._ensure_connected()
        return sdb.query('SELECT `name`,`id_num` FROM `sp_tags` ORDER BY `id_num` DESC LIMIT %d' % HOT_TAGS_NUM)
    
    def get_tag_by_name(self, name = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % name)

    def get_all_post_num(self, name = ''):
        obj = self.get_tag_by_name(name)
        if obj and obj.content:
            return len(obj.content.split(','))
        else:
            return 0
        
    def get_tag_page_posts(self, name = '', page = 1, limit = EACH_PAGE_POST_NUM):
        obj = self.get_tag_by_name(name)
        if obj and obj.content:
            page = int(page)
            idlist = obj.content.split(',')
            getids = idlist[limit*(page-1):limit*page]
            sdb._ensure_connected()
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(getids), len(getids))))
        else:
            return []
            
    def add_postid_to_tags(self, tags = [], postid = ''):
        mdb._ensure_connected()
        for tag in tags:
            obj = mdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % tag)
            
            if obj:
                query = "UPDATE `sp_tags` SET `id_num` = `id_num` + 1, `content` =  concat(%s, `content`) WHERE `id` = %s LIMIT 1"
                mdb.execute(query, "%s,"%postid, obj.id)
            else:
                query = "INSERT INTO `sp_tags` (`name`,`id_num`,`content`) values(%s,1,%s)"
                mdb.execute(query, tag, postid)
        
    def remove_postid_from_tags(self, tags = [], postid = ''):
        mdb._ensure_connected()
        for tag in tags:
            obj = mdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % tag)
            
            if obj:
                idlist = obj.content.split(',')
                if postid in idlist:
                    idlist.remove(postid)
                    try:
                        idlist.remove('')
                    except:
                        pass
                    if len(idlist) == 0:
                        mdb.execute("DELETE FROM `sp_tags` WHERE `id` = %s LIMIT 1", obj.id)
                    else:
                        query = "UPDATE `sp_tags` SET `id_num` = %s, `content` =  %s WHERE `id` = %s LIMIT 1"
                        mdb.execute(query, len(idlist), ','.join(idlist), obj.id)                
                else:
                    pass            

Tag = Tag()

class User():
    def check_has_user(self):
        sdb._ensure_connected()
        return sdb.get('SELECT `id` FROM `sp_user` LIMIT 1')

    def get_all_user(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_user`')

    def get_user_by_name(self, name):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_user` WHERE `name` = \'%s\' LIMIT 1' % str(name))

    def add_new_user(self, name = '', pw = ''):
        if name and pw:
            query = "insert into `sp_user` (`name`,`password`) values(%s,%s)"
            mdb._ensure_connected()
            return mdb.execute(query, name, md5(pw.encode('utf-8')).hexdigest())
        else:
            return None
        
    def check_user(self, name = '', pw = ''):
        if name and pw:
            user = self.get_user_by_name(name)
            if user and user.name == name and user.password == pw:
                return True
            else:
                return False
        else:
            return False

User = User()

class MyData():
    def flush_all_data(self):
        sql = """
        TRUNCATE TABLE `sp_category`;
        TRUNCATE TABLE `sp_comments`;
        TRUNCATE TABLE `sp_links`;
        TRUNCATE TABLE `sp_posts`;
        TRUNCATE TABLE `sp_tags`;
        TRUNCATE TABLE `sp_user`;
        """
        mdb._ensure_connected()
        mdb.execute(sql)
        
    def creat_table(self):
        sql = """
DROP TABLE IF EXISTS `sp_category`;
CREATE TABLE IF NOT EXISTS `sp_category` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(17) NOT NULL DEFAULT '',
  `id_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_comments`;
CREATE TABLE IF NOT EXISTS `sp_comments` (
  `id` int(8) unsigned NOT NULL AUTO_INCREMENT,
  `postid` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `author` varchar(20) NOT NULL,
  `email` varchar(30) NOT NULL,
  `url` varchar(75) NOT NULL,
  `visible` tinyint(1) NOT NULL DEFAULT '1',
  `add_time` int(10) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `postid` (`postid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_links`;
CREATE TABLE IF NOT EXISTS `sp_links` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `displayorder` tinyint(3) NOT NULL DEFAULT '0',
  `name` varchar(100) NOT NULL DEFAULT '',
  `url` varchar(200) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_posts`;
CREATE TABLE IF NOT EXISTS `sp_posts` (
  `id` mediumint(8) unsigned NOT NULL AUTO_INCREMENT,
  `category` varchar(17) NOT NULL DEFAULT '',
  `title` varchar(100) NOT NULL DEFAULT '',
  `content` mediumtext NOT NULL,
  `comment_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `closecomment` tinyint(1) NOT NULL DEFAULT '0',
  `tags` varchar(100) NOT NULL,
  `password` varchar(8) NOT NULL DEFAULT '',
  `add_time` int(10) unsigned NOT NULL DEFAULT '0',
  `edit_time` int(10) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `category` (`category`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_tags`;
CREATE TABLE IF NOT EXISTS `sp_tags` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(17) NOT NULL DEFAULT '',
  `id_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`),
  KEY `id_num` (`id_num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_user`;
CREATE TABLE IF NOT EXISTS `sp_user` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL DEFAULT '',
  `password` varchar(32) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

"""
        mdb._ensure_connected()
        mdb.execute(sql)
        
MyData = MyData()
