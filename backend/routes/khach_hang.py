from flask import Blueprint, request, jsonify
from config import get_connection
import hashlib

khach_hang_bp = Blueprint('khach_hang', __name__)

@khach_hang_bp.route('/dang-ky', methods=['POST'])
def dang_ky():
    data     = request.json
    ho_ten   = data.get('ho_ten')
    email    = data.get('email')
    mat_khau = data.get('mat_khau')
    sdt      = data.get('so_dien_thoai')

    if not ho_ten or not email or not mat_khau:
        return jsonify({'error': 'Thiếu thông tin đăng ký'}), 400

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id FROM khach_hang WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({'error': 'Email đã tồn tại'}), 409

    mk_hash = hashlib.sha256(mat_khau.encode()).hexdigest()
    cursor.execute("""
        INSERT INTO khach_hang (ho_ten, email, mat_khau_hash, so_dien_thoai)
        VALUES (%s, %s, %s, %s)
    """, (ho_ten, email, mk_hash, sdt))
    conn.commit()
    return jsonify({'success': True, 'message': 'Đăng ký thành công!'})


@khach_hang_bp.route('/dang-nhap', methods=['POST'])
def dang_nhap():
    data     = request.json
    email    = data.get('email')
    mat_khau = data.get('mat_khau')

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    mk_hash = hashlib.sha256(mat_khau.encode()).hexdigest()
    cursor.execute("""
        SELECT id, ho_ten, email, so_dien_thoai
        FROM khach_hang
        WHERE email = %s AND mat_khau_hash = %s
    """, (email, mk_hash))
    kh = cursor.fetchone()

    if not kh:
        return jsonify({'error': 'Email hoặc mật khẩu không đúng'}), 401

    return jsonify({'success': True, 'khach_hang': kh})


@khach_hang_bp.route('/<int:kh_id>/lich-su', methods=['GET'])
def lich_su(kh_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT dv.ma_dat_ve, dv.loai_chuyen, dv.tong_tien,
               dv.trang_thai, dv.ngay_dat
        FROM dat_ve dv
        WHERE dv.khach_hang_id = %s
        ORDER BY dv.ngay_dat DESC
    """, (kh_id,))
    data = cursor.fetchall()
    for d in data:
        d['ngay_dat'] = str(d['ngay_dat'])
    cursor.close()
    conn.close()
    return jsonify(data)
    # Cập nhật thông tin
@khach_hang_bp.route('/<int:kh_id>/cap-nhat', methods=['PUT'])
def cap_nhat(kh_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        UPDATE khach_hang SET
            ho_ten=%s, so_dien_thoai=%s, ngay_sinh=%s,
            gioi_tinh=%s, quoc_tich=%s, so_ho_chieu=%s
        WHERE id = %s
    """, (data.get('ho_ten'), data.get('so_dien_thoai'),
          data.get('ngay_sinh') or None, data.get('gioi_tinh'),
          data.get('quoc_tich'), data.get('so_ho_chieu'), kh_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True})


# Đổi mật khẩu
@khach_hang_bp.route('/<int:kh_id>/doi-mat-khau', methods=['PUT'])
def doi_mat_khau(kh_id):
    import hashlib
    data = request.json
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    mk_cu_hash = hashlib.sha256(data.get('mat_khau_cu').encode()).hexdigest()
    cursor.execute("SELECT id FROM khach_hang WHERE id=%s AND mat_khau_hash=%s", (kh_id, mk_cu_hash))
    if not cursor.fetchone():
        return jsonify({'error': 'Mật khẩu hiện tại không đúng!'}), 400
    mk_moi_hash = hashlib.sha256(data.get('mat_khau_moi').encode()).hexdigest()
    cursor.execute("UPDATE khach_hang SET mat_khau_hash=%s WHERE id=%s", (mk_moi_hash, kh_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True})