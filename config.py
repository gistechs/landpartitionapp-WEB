class Config(object):

    DEBUG = False
    TESTING = False

    SECRET_KEY = "703ad7d4ea5f8357f2666d802155be45"
    SAMPLE_FOLDER = "static/sample"
    UPLOAD_FOLDER = "static/shp"
    UPLOAD_FOLDER_PR = "static/shp/upload_pr"
    UPLOAD_FOLDER_RZ = "static/shp/upload_rz"   
    ALLOWED_EXTENSIONS = {'zip'}

    SESSION_COOKIE_SECURE = True


class ProductionConfig(Config):
    pass


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    TESTING = True
    SESSION_COOKIE_SECURE = False
