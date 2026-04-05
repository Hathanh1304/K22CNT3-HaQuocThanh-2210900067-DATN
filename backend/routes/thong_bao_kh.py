from flask import Blueprint, request, jsonify
from config import get_connection

thong_bao_bp = Blueprint('thong_bao', __name__)

# Lấy thông báo của khách hàng
@thong_bao_bp.route('/cua-toi/<int:kh_id>', methods=['GET'])
def thong_bao_cua_toi(kh_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, tieu_de, noi_dung, loai, trang_thai, ngay_tao
            FROM thong_bao
            WHERE khach_hang_id = %s OR khach_hang_id IS NULL
            ORDER BY ngay_tao DESC
            LIMIT 20
        """, (kh_id,))
        data = cursor.fetchall()
        for d in data:
            d['ngay_tao'] = str(d['ngay_tao'])
        return jsonify(data)
    finally:
        cursor.close()
        conn.close()

# Đánh dấu 1 thông báo đã đọc
@thong_bao_bp.route('/doc/<int:tb_id>', methods=['PUT'])
def doc_thong_bao(tb_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE thong_bao SET trang_thai='da_doc' WHERE id=%s", (tb_id,))
        conn.commit()
        return jsonify({'success': True})
    finally:
        cursor.close()
        conn.close()

# Đánh dấu tất cả đã đọc
@thong_bao_bp.route('/doc-tat-ca/<int:kh_id>', methods=['PUT'])
def doc_tat_ca(kh_id):
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Không kết nối được database'}), 500
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE thong_bao SET trang_thai='da_doc'
            WHERE (khach_hang_id=%s OR khach_hang_id IS NULL)
              AND trang_thai='chua_doc'
        """, (kh_id,))
        conn.commit()
        return jsonify({'success': True})
    finally:
        cursor.close()
        conn.close()