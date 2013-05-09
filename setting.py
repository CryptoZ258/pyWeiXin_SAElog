# -*- coding: utf-8 -*-
from os import environ

SAEPY_LOG_VERSION = '0.0.2' # 当前SAEpy-log版本
APP_NAME = environ.get("APP_NAME", "")
debug = not APP_NAME

##下面需要修改
SITE_TITLE = u"南苑随笔" #博客标题
SITE_TITLE2 = u"青春奋进" #显示在边栏上头（有些模板用不到）
SITE_SUB_TITLE = u"记录我们南苑里的点点滴滴" #副标题
KEYWORDS = u"南苑，随笔，微信，趣事" #博客关键字
SITE_DECR = u"提供南苑最新资讯，学习，科研，趣闻" #博客描述，给搜索引擎看
ADMIN_NAME = u"ugeekers" #发博文的作者
NOTICE_MAIL = u"ugeekers@gmail.com" #常用的，容易看到的接收提醒邮件，如QQ 邮箱，仅作收件用

###配置邮件发送信息，提醒邮件用的，必须正确填写，建议用Gmail
MAIL_FROM = 'ugeekers@gmail.com' #xxx@gmail.com
MAIL_SMTP = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_PASSWORD = 'email_password' #你的邮箱登录密码，用以发提醒邮件

#放在网页底部的统计代码
ANALYTICS_CODE = """
<script type="text/javascript">
var _bdhmProtocol = (("https:" == document.location.protocol) ? " https://" : " http://");
document.write(unescape("%3Cscript src='" + _bdhmProtocol + "hm.baidu.com/h.js%3F4feb6150395fa48b6494812f2e7a724d' type='text/javascript'%3E%3C/script%3E"));
</script>
""" 


#使用SAE Storage 服务（保存上传的附件），需在SAE管理面板创建
STORAGE_DOMAIN_NAME = 'attachment' 

###设置容易调用的jquery 文件
JQUERY = "http://lib.sinaapp.com/js/jquery/1.6.2/jquery.min.js"
#JQUERY = "http://code.jquery.com/jquery-1.6.2.min.js"
#JQUERY = "/static/jquery-plugin/jquery-1.6.4.js"

COPY_YEAR = '2013' #页脚的 © 2011 

MAJOR_DOMAIN = '%s.sinaapp.com' % APP_NAME #主域名，默认是SAE 的二级域名
#MAJOR_DOMAIN = 'www.yourdomain.com'

##博客使用的主题，目前可选 default/octopress/octopress-disqus
##你也可以把自己喜欢的wp主题移植过来，
#制作方法参见 http://saepy.sinaapp.com/t/49
THEME = 'octopress'

#使用disqus 评论系统，如果你使用就填 website shortname，
#申请地址 http://disqus.com/
DISQUS_WEBSITE_SHORTNAME = ''

####友情链接列表，在管理后台也实现了管理，下面的链接列表仍然有效并排在前面
LINK_BROLL = [
    {"text": 'SAEpy blog', "url": 'http://saepy.sinaapp.com'},
    {"text": 'Sina App Engine', "url": 'http://sae.sina.com.cn/'},    
]

#当发表新博文时自动ping RPC服务，中文的下面三个差不多了
XML_RPC_ENDPOINTS = [
    'http://blogsearch.google.com/ping/RPC2', 
    'http://rpc.pingomatic.com/', 
    'http://ping.baidu.com/ping/RPC2'
]

##如果要在本地测试则需要配置Mysql 数据库信息
if debug:
    MYSQL_DB = 'app_db_name'
    MYSQL_USER = 'root'
    MYSQL_PASS = 'pass'
    MYSQL_HOST_M = '127.0.0.1'
    MYSQL_HOST_S = '127.0.0.1'
    MYSQL_PORT = '3306'

####除了修改上面的设置，你还需在SAE 后台开通下面几项服务：
# 1 初始化 Mysql
# 2 建立一个名为 attachment 的 Storage
# 3 启用Memcache，初始化大小为1M的 mc，大小可以调，日后文章多了，PV多了可增加
# 4 创建一个 名为 default 的 Task Queue
# 详见 http://saepy.sinaapp.com/t/50 详细安装指南
############## 下面不建议修改 ###########################
if debug:
    BASE_URL = 'http://127.0.0.1:8080'
else:
    BASE_URL = 'http://%s'%MAJOR_DOMAIN

LANGUAGE = 'zh-CN'
COMMENT_DEFAULT_VISIBLE = 1 #0/1 #发表评论时是否显示 设为0时则需要审核才显示
EACH_PAGE_POST_NUM = 7 #每页显示文章数
EACH_PAGE_COMMENT_NUM = 10 #每页评论数
RELATIVE_POST_NUM = 5 #显示相关文章数
SHORTEN_CONTENT_WORDS = 150 #文章列表截取的字符数
DESCRIPTION_CUT_WORDS = 100 #meta description 显示的字符数
RECENT_COMMENT_NUM = 5 #边栏显示最近评论数
RECENT_COMMENT_CUT_WORDS = 20 #边栏评论显示字符数
LINK_NUM = 30 #边栏显示的友情链接数
MAX_COMMENT_NUM_A_DAY = 10 #客户端设置Cookie 限制每天发的评论数

PAGE_CACHE = not debug #本地没有Memcache 服务
PAGE_CACHE_TIME = 3600*24 #默认页面缓存时间 

HOT_TAGS_NUM = 100 #右侧热门标签显示数

MAX_IDLE_TIME = 5 #数据库最大空闲时间 SAE文档说是30 其实更小，设为5，没问题就不要改了
