from flask import Blueprint, request, jsonify
from config import get_connection
import hashlib

auth_admin_bp = Blueprint('auth_admin', __name__)

# Đăng nhập Admin
@auth_admin_bp.route('/dang-nhap', methods=['POST'])
def dang_nhap_admin():
    data          = request.json
    ten_dang_nhap = data.get('ten_dang_nhap')
    mat_khau      = data.get('mat_khau')

    if not ten_dang_nhap or not mat_khau:
        return jsonify({'error': 'Thiếu thông tin đăng nhập'}), 400

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    mk_hash = hashlib.sha256(mat_khau.encode()).hexdigest()

    cursor.execute("""
        SELECT id, ten_dang_nhap, ho_ten, email, vai_tro
        FROM admin
        WHERE ten_dang_nhap = %s
          AND mat_khau_hash = %s
          AND trang_thai = 1
    """, (ten_dang_nhap, mk_hash))
    admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if not admin:
        return jsonify({'error': 'Tên đăng nhập hoặc mật khẩu không đúng!'}), 401

    return jsonify({'success': True, 'admin': admin})


# Đổi mật khẩu Admin
@auth_admin_bp.route('/doi-mat-khau', methods=['PUT'])
def doi_mat_khau_admin():
    data    = request.json
    admin_id = data.get('admin_id')
    mk_cu   = data.get('mat_khau_cu')
    mk_moi  = data.get('mat_khau_moi')

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    mk_cu_hash = hashlib.sha256(mk_cu.encode()).hexdigest()

    cursor.execute("SELECT id FROM admin WHERE id = %s AND mat_khau_hash = %s", (admin_id, mk_cu_hash))
    if not cursor.fetchone():
        return jsonify({'error': 'Mật khẩu hiện tại không đúng!'}), 400

    mk_moi_hash = hashlib.sha256(mk_moi.encode()).hexdigest()
    cursor.execute("UPDATE admin SET mat_khau_hash = %s WHERE id = %s", (mk_moi_hash, admin_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'success': True})