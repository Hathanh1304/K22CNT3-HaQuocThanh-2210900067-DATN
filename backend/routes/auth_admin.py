from flask import Blueprint, request, jsonify
from config import get_connection
import hashlib

auth_admin_bp = Blueprint('auth_admin', __name__)

@auth_admin_bp.route('/dang-nhap', methods=['POST'])
def dang_nhap_admin():
    data     = request.json
    ten      = data.get('ten_dang_nhap')
    mat_khau = data.get('mat_khau')

    if not ten or not mat_khau:
        return jsonify({'error': 'Thiếu thông tin đăng nhập'}), 400

    mk_hash = hashlib.sha256(mat_khau.encode()).hexdigest()

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, ten_dang_nhap, ho_ten, email, vai_tro
            FROM admin
            WHERE ten_dang_nhap = %s AND mat_khau_hash = %s AND trang_thai = 1
        """, (ten, mk_hash))
        admin = cursor.fetchone()

        if not admin:
            return jsonify({'error': 'Tên đăng nhập hoặc mật khẩu không đúng!'}), 401

        return jsonify({'success': True, 'admin': admin})
    finally:
        cursor.close()
        conn.close()