# -*- coding: utf-8 -*-

import logging

import json
    
from hashlib import md5
from time import time

from setting import *

from common import BaseHandler, unquoted_unicode, quoted_string, safe_encode, slugfy, pagecache, clear_cache_by_pathlist, client_cache

from model import Article, Comment, Link, Category, Tag

# weixin used package
import xml.etree.ElementTree as ET  
import urllib,urllib2,time,hashlib

import tornado.wsgi
import tornado.escape


TOKEN = "bibodeng"
PIC_URL = "http://scnuwriter-attachment.stor.sinaapp.com/1367903537.jpg"
SORRY="sorry 没找到,尝试回复h得到帮助"
MAX_ARTICLE = 5

###############
class HomePage(BaseHandler):
    @pagecache()
    def get(self):
        try:
            objs = Article.get_post_for_homepage()
        except:
            self.redirect('/install')
            return
        if objs:
            fromid = objs[0].id
            endid = objs[-1].id
        else:
            fromid = endid = ''
        
        allpost =  Article.count_all_post()
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
        
        output = self.render('index.html', {
            'title': "%s - %s"%(SITE_TITLE,SITE_SUB_TITLE),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'index',
            'fromid': fromid,
            'endid': endid,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output

class IndexPage(BaseHandler):
    @pagecache('post_list_index', PAGE_CACHE_TIME, lambda self,direction,page,base_id: page)
    def get(self, direction = 'next', page = '2', base_id = '1'):
        if page == '1':
            self.redirect(BASE_URL)
            return
        objs = Article.get_page_posts(direction, page, base_id)
        if objs:
            if direction == 'prev':
                objs.reverse()            
            fromid = objs[0].id
            endid = objs[-1].id
        else:
            fromid = endid = ''
        
        allpost =  Article.count_all_post()
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
        output = self.render('index.html', {
            'title': "%s - %s | Part %s"%(SITE_TITLE,SITE_SUB_TITLE, page),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': int(page),
            'allpage': allpage,
            'listtype': 'index',
            'fromid': fromid,
            'endid': endid,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        
class PostDetailShort(BaseHandler):
    @client_cache(600, 'public')
    def get(self, id = ''):
        obj = Article.get_article_by_id_simple(id)
        if obj:
            self.redirect('%s/topic/%d/%s'% (BASE_URL, obj.id, obj.title), 301)
            return
        else:
            self.redirect(BASE_URL)

class PostDetail(BaseHandler):
    @pagecache('post', PAGE_CACHE_TIME, lambda self,id,title: id)
    def get(self, id = '', title = ''):
        tmpl = ''
        obj = Article.get_article_by_id_detail(id)
        if not obj:
            self.redirect(BASE_URL)
            return
        #redirect to right title
        try:
            title = unquote(title).decode('utf-8')
        except:
            pass
        if title != obj.slug:
            self.redirect(obj.absolute_url, 301)
            return        
        #
        if obj.password and THEME == 'default':
            rp = self.get_cookie("rp%s" % id, '')
            if rp != obj.password:
                tmpl = '_pw'
        
        self.set_header("Last-Modified", obj.last_modified)
            
        output = self.render('page%s.html'%tmpl, {
            'title': "%s - %s"%(obj.title, SITE_TITLE),
            'keywords':obj.keywords,
            'description':obj.description,
            'obj': obj,
            'cobjs': obj.coms,
            'postdetail': 'postdetail',
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': 10,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        
        if obj.password and THEME == 'default':
            return
        else:
            return output
        
    def post(self, id = '', title = ''):
        action = self.get_argument("act")
        
        if action == 'inputpw':
            wrn = self.get_cookie("wrpw", '0')
            if int(wrn)>=10:
                self.write('403')
                return
            
            pw = self.get_argument("pw",'')
            pobj = Article.get_article_by_id_simple(id)
            wr = False
            if pw:             
                if pobj.password == pw:
                    self.set_cookie("rp%s" % id, pobj.password, path = "/", expires_days =1)
                else:
                    wr = True
            else:
                wr = True
            if wr:
                wrn = self.get_cookie("wrpw", '0')
                self.set_cookie("wrpw", str(int(wrn)+1), path = "/", expires_days = 1 )
            
            self.redirect('%s/topic/%d/%s'% (BASE_URL, pobj.id, pobj.title))
            return
        
        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}
        
        if action == 'readmorecomment':
            fromid = self.get_argument("fromid",'')
            allnum = int(self.get_argument("allnum",0))
            showednum = int(self.get_argument("showednum", EACH_PAGE_COMMENT_NUM))
            if fromid:
                rspd['status'] = 200
                if (allnum - showednum) >= EACH_PAGE_COMMENT_NUM:
                    limit = EACH_PAGE_COMMENT_NUM
                else:
                    limit = allnum - showednum
                cobjs = Comment.get_post_page_comments_by_id( id, fromid, limit )
                rspd['commentstr'] = self.render('comments.html', {'cobjs': cobjs})
                rspd['lavenum'] = allnum - showednum - limit
                self.write(json.dumps(rspd))
            return
        
        #
        usercomnum = self.get_cookie('usercomnum','0')
        if int(usercomnum) > MAX_COMMENT_NUM_A_DAY:
            rspd = {'status': 403, 'msg':'403: Forbidden'}
            self.write(json.dumps(rspd))
            return
        
        try:
            timestamp = int(time())
            post_dic = {
                'author': self.get_argument("author"),
                'email': self.get_argument("email"),
                'content': safe_encode(self.get_argument("con").replace('\r','\n')),
                'url': self.get_argument("url",''),
                'postid': self.get_argument("postid"),
                'add_time': timestamp,
                'toid': self.get_argument("toid",''),
                'visible': COMMENT_DEFAULT_VISIBLE
            }
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return
        
        pobj = Article.get_article_by_id_simple(id)
        if pobj and not pobj.closecomment:
            cobjid = Comment.add_new_comment(post_dic)
            if cobjid:
                Article.update_post_comment( pobj.comment_num+1, id)
                rspd['status'] = 200
                #rspd['msg'] = '恭喜： 已成功提交评论'
                
                rspd['msg'] = self.render('comment.html', {
                        'cobjid': cobjid,
                        'gravatar': 'http://www.gravatar.com/avatar/%s'%md5(post_dic['email']).hexdigest(),
                        'url': post_dic['url'],
                        'author': post_dic['author'],
                        'visible': post_dic['visible'],
                        'content': post_dic['content'],
                    })
                
                clear_cache_by_pathlist(['/','post:%s'%id])
                #send mail
                if not debug:
                    try:
                        if NOTICE_MAIL:
                            tolist = [NOTICE_MAIL]
                        else:
                            tolist = []
                        if post_dic['toid']:
                            tcomment = Comment.get_comment_by_id(toid)
                            if tcomment and tcomment.email:
                                tolist.append(tcomment.email)
                        commenturl = "%s/t/%s#r%s" % (BASE_URL, str(pobj.id), str(cobjid))
                        m_subject = u'有人回复您在 《%s》 里的评论 %s' % ( pobj.title,str(cobjid))
                        m_html = u'这是一封提醒邮件（请勿直接回复）： %s ，请尽快处理： %s' % (m_subject, commenturl)
                        
                        if tolist:
                            import sae.mail
                            sae.mail.send_mail(','.join(tolist), m_subject, m_html,(MAIL_SMTP, int(MAIL_PORT), MAIL_FROM, MAIL_PASSWORD, True))          
                        
                    except:
                        pass
            else:
                rspd['msg'] = '错误： 未知错误'
        else:
            rspd['msg'] = '错误： 未知错误'
        self.write(json.dumps(rspd))

class CategoryDetailShort(BaseHandler):
    @client_cache(3600, 'public')
    def get(self, id = ''):
        obj = Category.get_cat_by_id(id)
        if obj:
            self.redirect('%s/category/%s'% (BASE_URL, obj.name), 301)
            return
        else:
            self.redirect(BASE_URL)

class CategoryDetail(BaseHandler):
    @pagecache('cat', PAGE_CACHE_TIME, lambda self,name: name)
    def get(self, name = ''):
        objs = Category.get_cat_page_posts(name, 1)
        
        catobj = Category.get_cat_by_name(name)
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s"%( catobj.name, SITE_TITLE),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'cat',
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output

class TagDetail(BaseHandler):
    @pagecache()
    def get(self, name = ''):
        objs = Tag.get_tag_page_posts(name, 1)
        
        catobj = Tag.get_tag_by_name(name)
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s"%( catobj.name, SITE_TITLE),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'tag',
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        

class ArticleList(BaseHandler):
    @pagecache('post_list_tag', PAGE_CACHE_TIME, lambda self,listtype,direction,page,name: "%s_%s"%(name,page))
    def get(self, listtype = '', direction = 'next', page = '1', name = ''):
        if listtype == 'cat':
            objs = Category.get_cat_page_posts(name, page)
            catobj = Category.get_cat_by_name(name)
        else:
            objs = Tag.get_tag_page_posts(name, page)
            catobj = Tag.get_tag_by_name(name)
        
        #
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s | Part %s"%( catobj.name, SITE_TITLE, page),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': int(page),
            'allpage': allpage,
            'listtype': listtype,
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        
        
class Robots(BaseHandler):
    def get(self):
        self.echo('robots.txt',{'cats':Category.get_all_cat_id()})

class Feed(BaseHandler):
    def get(self):
        posts = Article.get_post_for_homepage()
        output = self.render('index.xml', {
                    'posts':posts,
                    'site_updated':Article.get_last_post_add_time(),
                })
        self.set_header('Content-Type','application/atom+xml')
        self.write(output)        

class Sitemap(BaseHandler):
    def get(self, id = ''):
        self.set_header('Content-Type','text/xml')
        self.echo('sitemap.html', {'sitemapstr':Category.get_sitemap_by_id(id), 'id': id})

class Attachment(BaseHandler):
    def get(self, name):
        self.redirect('http://%s-%s.stor.sinaapp.com/%s'% (APP_NAME, STORAGE_DOMAIN_NAME, unquoted_unicode(name)), 301)
        return
        
# 添加微信推送帐号
class WeiXinPoster(BaseHandler):
	#-----------------------------------------------------------------------
	# 处理get方法 对应check_signature
	def get(self):
		global TOKEN  
		signature = self.get_argument("signature")
		timestamp = self.get_argument("timestamp")
		nonce = self.get_argument("nonce")
		echoStr = self.get_argument("echostr")
		token = TOKEN  
		tmpList = [token,timestamp,nonce]  
		tmpList.sort()  
		tmpstr = "%s%s%s" % tuple(tmpList)  
		tmpstr = hashlib.sha1(tmpstr).hexdigest()

		if tmpstr == signature: 
			self.write(echoStr) 
			#return echoStr
		else:  
			self.write(None);
			#return None
			
	# 处理post方法,对应response_msg
	def post(self):
		global SORRY
		# 从request中获取请求文本
		rawStr = self.request.body
		# 将文本进行解析,得到请求的数据
		msg = self.parse_request_xml(ET.fromstring(rawStr))
		# 根据请求消息来处理内容返回
		query_str = msg.get("Content")
		query_str = tornado.escape.utf8(query_str)
		# TODO 用户发来的数据类型可能多样，所以需要判别
		response_msg = ""
		return_data = ""
		# 使用简单的处理逻辑，有待扩展
		if query_str[0] == "h":		# send help menu to user
			response_msg = self.get_help_menu()		# 返回消息
			# 包括post_msg，和对应的 response_msg
			if response_msg:
				return_data = self.pack_text_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
		# 分类
		elif query_str[0] =="c":
			category = query_str[1:]
			response_msg = self.get_category_articles(category)
			if response_msg:
				return_data = self.pack_news_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
		# 列出文章列表	
		elif query_str[0] =="l":
			response_msg = self.get_article_list()
			if response_msg:
				return_data = self.pack_text_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
		# 直接获取某篇文章	
		elif query_str[0] == "a":
			# 直接获取文章的id，然后在数据库中查询
			article_id = int(query_str[1:])
			# 进行操作
			response_msg = self.get_response_article_by_id(article_id)
			if response_msg:
				return_data = self.pack_news_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
			
		# 还要考虑其他
		elif query_str[0] == "s":
			keyword = str(query_str[1:])
			# 搜索关键词，返回相关文章
			response_msg = self.get_response_article(keyword)
			# 返回图文信息
			if response_msg:
				return_data = self.pack_news_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
			
		elif query_str[0] == "n":
			response_msg = self.get_latest_articles()
			# 返回图文信息
			if response_msg:
				return_data = self.pack_news_xml(msg, response_msg)
			else:
				response_msg = SORRY
				return_data = self.pack_text_xml(msg, response_msg)
			self.write(return_data)
		# 如果找不到，返回帮助信息
		else:
			response_msg = get_help_menu()
			if response_msg:
				return_data = response_msg
			else:
				return_data = SORRY
			self.write(return_data)
	# n for 获取最新的文章
	def get_latest_articles(self):
		global MAX_ARTICLE
		global PIC_URL
		article_list = Article.get_articles_by_latest()
		article_list_length = len(article_list)
		count = (article_list_length < MAX_ARTICLE) and article_list_length or MAX_ARTICLE
		if article_list:
			# 构造图文消息
			articles_msg = {'articles':[]}
			for i in range(0,count):
				article = {
						'title': article_list[i].slug,
						'description':article_list[i].description,
						'picUrl':PIC_URL,
						'url':article_list[i].absolute_url
					}
				# 插入文章
				articles_msg['articles'].append(article)
				article = {}
			# 返回文章
			return articles_msg
	
	#-----------------------------------------------------------------------
	# 解析请求,拆解到一个字典里        
	def parse_request_xml(self,root_elem):
		msg = {}
		if root_elem.tag == 'xml':
			for child in root_elem:
				msg[child.tag] = child.text  # 获得内容  
			return msg

	#-----------------------------------------------------------------------
	def get_help_menu(self):
		menu_msg = '''欢迎关注南苑随笔，在这里你能获得关于校园的资讯和故事。回复如下按键则可以完成得到相应的回应
		h ：帮助(help)
		l ：文章列表(article list)
		f : 获得分类列表
		n : 获取最新文章
		a + 数字 ：察看某篇文章 a2 察看第2篇文章
		s + 关键字 : 搜索相关文章 s科研 察看科研相关
		c + 分类名 ： 获取分类文章 c校园生活 察看校园生活分类
		其他 ： 功能有待丰富'''
		return menu_msg
	#-----------------------------------------------------------------------
	# 获取文章列表
	def get_article_list(self):
		# 查询数据库获取文章列表 
		article_list = Article.get_all_article_list()
		article_list_str = "最新文章列表供您点阅，回复a+数字即可阅读: \n"
		for i in range(len(article_list)):
			art_id = str(article_list[i].id)
			art_id = tornado.escape.native_str(art_id)
			
			art_title = article_list[i].title
			art_title = tornado.escape.native_str(art_title)
			
			art_category = article_list[i].category
			art_category = tornado.escape.native_str(art_category)
			
			
			article_list_str +=  art_id + ' ' + art_title + ' ' + art_category + '\n'
		return article_list_str
		
	# 按照分类查找
	def get_category_articles(self, category):
		global MAX_ARTICLE
		global PIC_URL
		article_list = Article.get_articles_by_category(category)
		article_list_length = len(article_list)
		count = (article_list_length < MAX_ARTICLE) and article_list_length or MAX_ARTICLE
		if article_list:
			# 构造图文消息
			articles_msg = {'articles':[]}
			for i in range(0,count):
				article = {
						'title': article_list[i].slug,
						'description':article_list[i].description,
						'picUrl':PIC_URL,
						'url':article_list[i].absolute_url
					}
				# 插入文章
				articles_msg['articles'].append(article)
				article = {}
			# 返回文章
			return articles_msg
	#-----------------------------------------------------------------------
	# 获取用于返回的msg
	def get_response_article(self, keyword):
		global PIC_URL
		keyword = str(keyword)
		# 从数据库查询得到若干文章
		article = Article.get_article_by_keyword(keyword)
		# 这里先用测试数据
		if article:
			title = article.slug
			description = article.description
			picUrl = PIC_URL
			url = article.absolute_url
			count = 1
			# 也有可能是若干篇
			# 这里实现相关逻辑，从数据库中获取内容
			
			# 构造图文消息
			articles_msg = {'articles':[]}
			for i in range(0,count):
				article = {
						'title':title,
						'description':description,
						'picUrl':picUrl,
						'url':url
					}
				# 插入文章
				articles_msg['articles'].append(article)
				article = {}
			# 返回文章
			return articles_msg
		else:
			return
	
	def get_response_article_by_id(self, post_id):
		global PIC_URL
		# 从数据库查询得到若干文章
		article = Article.get_article_by_id_detail(post_id)
		# postId为文章id
		if article:
			title = article.slug
			description = article.description
			picUrl = PIC_URL
			url = article.absolute_url
			count = 1
			# 这里实现相关逻辑，从数据库中获取内容
			
			# 构造图文消息
			articles_msg = {'articles':[]}
			for i in range(0,count):
				article = {
						'title':title,
						'description':description,
						'picUrl':picUrl,
						'url':url
					}
				# 插入文章
				articles_msg['articles'].append(article)
				article = {}
			# 返回文章
			return articles_msg
		else:
			return
	#-----------------------------------------------------------------------
	# 打包消息xml，作为返回	
	def pack_text_xml(self,post_msg,response_msg):
		# f = post_msg['FromUserName']
		# t = post_msg['FromUserName']
		text_tpl = '''<xml>
					<ToUserName><![CDATA[%s]]></ToUserName>
					<FromUserName><![CDATA[%s]]></FromUserName>
					<CreateTime>%s</CreateTime>
					<MsgType><![CDATA[%s]]></MsgType>
					<Content><![CDATA[%s]]></Content>
					<FuncFlag>0</FuncFlag>
					</xml>'''
		text_tpl = text_tpl % (post_msg['FromUserName'],post_msg['ToUserName'],str(int(time.time())),'text',response_msg)
		# 调换发送者和接收者，然后填入需要返回的信息到xml中
		return text_tpl

	#-----------------------------------------------------------------------	
	# 打包图文消息xml
	def pack_news_xml(self,post_msg,response_msg):
		articles = ''		# 文章部分
		article_tpl = '''<item>
					 <Title><![CDATA[%s]]></Title> 
					 <Description><![CDATA[%s]]></Description>
					 <PicUrl><![CDATA[%s]]></PicUrl>
					 <Url><![CDATA[%s]]></Url>
					 </item>'''
		# 在这里对aticle进行包装
		for i in range(0, len(response_msg['articles']) ):
			articles  += article_tpl % (response_msg['articles'][i]['title'],response_msg['articles'][i]['description'],
				response_msg['articles'][i]['picUrl'],response_msg['articles'][i]['url'])		# 连接
		# 将在article里面插入若干个item
		news_tpl = '''<xml>
					 <ToUserName><![CDATA[%s]]></ToUserName>
					 <FromUserName><![CDATA[%s]]></FromUserName>
					 <CreateTime>%s</CreateTime>
					 <MsgType><![CDATA[%s]]></MsgType>
					 <ArticleCount>%d</ArticleCount>
					 <Articles>
					 %s
					 </Articles>
					 <FuncFlag>1</FuncFlag>
					 </xml>'''
		# 填充内容到xml中
		news_tpl = news_tpl % (post_msg['FromUserName'],post_msg['ToUserName'],
				str(int(time.time())),'news',len(response_msg['articles']), articles)
		# 调换发送者和接收者，然后填入需要返回的信息到xml中
		return news_tpl

	#-----------------------------------------------------------------------
	# 打包图片消息xml
	def pack_pic_xml(self,post_msg,response_msg):
		img_tpl = '''<xml>
					<ToUserName><![CDATA[%s]]></ToUserName>
					<FromUserName><![CDATA[%s]]></FromUserName>
					<CreateTime>%s</CreateTime>
					<MsgType><![CDATA[%s]]></MsgType>
					<Content><![CDATA[%s]]></Content>
					<FuncFlag>0</FuncFlag>
					</xml>'''
		img_tpl = img_tpl % (post_msg['FromUserName'],post_msg['ToUserName'],str(int(time.time())),'image',response_msg)
		# 调换发送者和接收者，然后填入需要返回的信息到xml中
		return img_tpl

	#-----------------------------------------------------------------------	
	# 打包声音消息xml
	def pack_music_xml(self,post_msg,response_msg):
		music_tpl = '''<xml>
					<ToUserName><![CDATA[%s]]></ToUserName>
					<FromUserName><![CDATA[%s]]></FromUserName>
					<CreateTime>%s</CreateTime>
					<MsgType><![CDATA[%s]]></MsgType>
					<Music>
					<Title><![CDATA[%s]]></Title>
					<Description><![CDATA[%s]]></Description>
					<MusicUrl><![CDATA[%s]]></MusicUrl>
					<HQMusicUrl><![CDATA[%s]]></HQMusicUrl>
					</Music>
					<FuncFlag>0</FuncFlag>
					</xml>'''
		music_tpl = music_tpl % (post_msg['FromUserName'],post_msg['ToUserName'],str(int(time.time())),'music',response_msg)
		# 调换发送者和接收者，然后填入需要返回的信息到xml中
		return music_tpl

		
########
urls = [
    (r"/", HomePage),
    (r"/robots.txt", Robots),
    (r"/feed", Feed),
    (r"/index.xml", Feed),
    (r"/t/(\d+)$", PostDetailShort),
    (r"/topic/(\d+)/(.*)$", PostDetail),
    (r"/index_(prev|next)_page/(\d+)/(\d+)/$", IndexPage),
    (r"/c/(\d+)$", CategoryDetailShort),
    (r"/category/(.+)/$", CategoryDetail),
    (r"/tag/(.+)/$", TagDetail),
    (r"/(cat|tag)_(prev|next)_page/(\d+)/(.+)/$", ArticleList),
    (r"/sitemap_(\d+)\.xml$", Sitemap),
    (r"/attachment/(.+)$", Attachment),
    (r"/weixin",WeiXinPoster),			# 添加微信url
]
