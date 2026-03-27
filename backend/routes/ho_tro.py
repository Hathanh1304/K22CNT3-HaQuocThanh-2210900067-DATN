from flask import Blueprint, request, jsonify
from config import get_connection

ho_tro_bp = Blueprint('ho_tro', __name__)

# Gửi yêu cầu hỗ trợ
@ho_tro_bp.route('/gui', methods=['POST'])
def gui_ho_tro():
    data = request.json
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO ho_tro (khach_hang_id, dat_ve_id, ho_ten, email, so_dien_thoai, loai, tieu_de, noi_dung)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('khach_hang_id'),
            data.get('dat_ve_id') or None,
            data.get('ho_ten'),
            data.get('email'),
            data.get('so_dien_thoai'),
            data.get('loai', 'hoi_thong_tin'),
            data.get('tieu_de'),
            data.get('noi_dung')
        ))
        conn.commit()
        ht_id = cursor.lastrowid
        return jsonify({'success': True, 'id': ht_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Lấy danh sách yêu cầu của khách hàng
@ho_tro_bp.route('/cua-toi/<int:kh_id>', methods=['GET'])
def ho_tro_cua_toi(kh_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, tieu_de, loai, trang_thai, noi_dung, phan_hoi, ngay_gui, ngay_xu_ly
        FROM ho_tro
        WHERE khach_hang_id = %s
        ORDER BY ngay_gui DESC
    """, (kh_id,))
    data = cursor.fetchall()
    for d in data:
        d['ngay_gui']   = str(d['ngay_gui'])
        d['ngay_xu_ly'] = str(d['ngay_xu_ly']) if d['ngay_xu_ly'] else None
    cursor.close()
    conn.close()
    return jsonify(data)

# Admin: lấy tất cả yêu cầu
@ho_tro_bp.route('/admin/danh-sach', methods=['GET'])
def admin_ds_ho_tro():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    trang_thai = request.args.get('trang_thai', '')
    sql = """
        SELECT ht.*, kh.ho_ten AS ten_kh
        FROM ho_tro ht
        LEFT JOIN khach_hang kh ON ht.khach_hang_id = kh.id
        WHERE (%s = '' OR ht.trang_thai = %s)
        ORDER BY ht.ngay_gui DESC
    """
    cursor.execute(sql, (trang_thai, trang_thai))
    data = cursor.fetchall()
    for d in data:
        d['ngay_gui']   = str(d['ngay_gui'])
        d['ngay_xu_ly'] = str(d['ngay_xu_ly']) if d['ngay_xu_ly'] else None
    cursor.close()
    conn.close()
    return jsonify(data)

# Admin: trả lời yêu cầu
@ho_tro_bp.route('/admin/tra-loi/<int:ht_id>', methods=['PUT'])
def tra_loi_ho_tro(ht_id):
    data = request.json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE ho_tro SET
                phan_hoi   = %s,
                trang_thai = %s,
                ngay_xu_ly = NOW()
            WHERE id = %s
        """, (data.get('phan_hoi'), data.get('trang_thai', 'da_xu_ly'), ht_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
