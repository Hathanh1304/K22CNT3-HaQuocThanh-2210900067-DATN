from flask import Flask
from flask_cors import CORS
from routes.chuyen_bay  import chuyen_bay_bp
from routes.dat_ve      import dat_ve_bp
from routes.khach_hang  import khach_hang_bp
from routes.thanh_toan  import thanh_toan_bp
from routes.admin       import admin_bp
from routes.auth_admin  import auth_admin_bp
from routes.ho_tro      import ho_tro_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(chuyen_bay_bp, url_prefix='/api/chuyen-bay')
app.register_blueprint(dat_ve_bp,     url_prefix='/api/dat-ve')
app.register_blueprint(khach_hang_bp, url_prefix='/api/khach-hang')
app.register_blueprint(thanh_toan_bp, url_prefix='/api/thanh-toan')
app.register_blueprint(auth_admin_bp, url_prefix='/api/auth-admin')
app.register_blueprint(admin_bp,      url_prefix='/api/admin')
app.register_blueprint(ho_tro_bp,     url_prefix='/api/ho-tro')

@app.route('/')
def index():
    return {'message': 'API Bán Vé Máy Bay đang chạy!'}

if __name__ == '__main__':
    app.run(debug=True, port=5000)