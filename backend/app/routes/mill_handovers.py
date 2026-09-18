from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.mill import Mill
from app.models.mill_handover import HANDOVER_SLOTS, MillHandover
from app.serializers import mill_handover_json
from app.utils import error, normalize_date

bp = Blueprint("mill_handovers", __name__, url_prefix="/api/mill-handovers")


def _read_fields(body: dict, db) -> tuple[dict | None, str | None]:
    try:
        mill_id = int(body.get("millId") or 0)
    except (TypeError, ValueError):
        return None, "请选择研磨机"
    if mill_id <= 0:
        return None, "请选择研磨机"

    mill = db.get(Mill, mill_id)
    if not mill:
        return None, "研磨机不存在"

    shift_date = normalize_date(str(body.get("shiftDate", "")))
    if shift_date is None:
        return None, "交接班日期无效，应为 YYYY-MM-DD"

    slot = str(body.get("slot", "")).strip()
    if slot not in HANDOVER_SLOTS:
        return None, "班次无效，应为 morning / afternoon / night"

    from_operator = str(body.get("fromOperator", "")).strip()
    if not from_operator:
        return None, "交班人不能为空"

    to_operator = str(body.get("toOperator", "")).strip()
    if not to_operator:
        return None, "接班人不能为空"

    note_raw = str(body.get("note") or "").strip()

    return (
        {
            "mill": mill,
            "shift_date": shift_date,
            "slot": slot,
            "from_operator": from_operator,
            "to_operator": to_operator,
            "note": note_raw or None,
        },
        None,
    )


def _duplicate(db, mill_id: int, shift_date, slot: str, exclude_id: int | None) -> bool:
    q = db.query(MillHandover).filter(
        MillHandover.mill_id == mill_id,
        MillHandover.shift_date == shift_date,
        MillHandover.slot == slot,
    )
    if exclude_id is not None:
        q = q.filter(MillHandover.id != exclude_id)
    return db.query(q.exists()).scalar()


@bp.get("")
@jwt_required()
def list_handovers():
    db = SessionLocal()
    try:
        q = db.query(MillHandover)

        mill_id_raw = request.args.get("millId", "").strip()
        if mill_id_raw:
            try:
                q = q.filter(MillHandover.mill_id == int(mill_id_raw))
            except ValueError:
                return error("millId 参数无效", 400)

        shift_date_raw = request.args.get("shiftDate", "").strip()
        if shift_date_raw:
            shift_date = normalize_date(shift_date_raw)
            if shift_date is None:
                return error("shiftDate 参数无效，应为 YYYY-MM-DD", 400)
            q = q.filter(MillHandover.shift_date == shift_date)

        rows = q.order_by(
            MillHandover.shift_date.desc(), MillHandover.slot.desc(), MillHandover.id.desc()
        ).all()
        return jsonify([mill_handover_json(r) for r in rows])
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_handover():
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        fields, err = _read_fields(body, db)
        if err:
            return error(err, 400)

        if _duplicate(db, fields["mill"].id, fields["shift_date"], fields["slot"], None):
            return error("该机台当日该班次已有交接班记录", 400)

        row = MillHandover(
            mill_id=fields["mill"].id,
            shift_date=fields["shift_date"],
            slot=fields["slot"],
            from_operator=fields["from_operator"],
            to_operator=fields["to_operator"],
            mill_status_snapshot=fields["mill"].status,
            note=fields["note"],
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该机台当日该班次已有交接班记录", 400)
        db.refresh(row)
        return jsonify(mill_handover_json(row)), 201
    finally:
        db.close()


@bp.put("/<int:item_id>")
@jwt_required()
def update_handover(item_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        row = db.get(MillHandover, item_id)
        if not row:
            return error("交接班记录不存在", 404)

        fields, err = _read_fields(body, db)
        if err:
            return error(err, 400)

        if _duplicate(
            db, fields["mill"].id, fields["shift_date"], fields["slot"], exclude_id=row.id
        ):
            return error("该机台当日该班次已有交接班记录", 400)

        row.mill_id = fields["mill"].id
        row.shift_date = fields["shift_date"]
        row.slot = fields["slot"]
        row.from_operator = fields["from_operator"]
        row.to_operator = fields["to_operator"]
        row.mill_status_snapshot = fields["mill"].status
        row.note = fields["note"]
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该机台当日该班次已有交接班记录", 400)
        db.refresh(row)
        return jsonify(mill_handover_json(row))
    finally:
        db.close()


@bp.delete("/<int:item_id>")
@jwt_required()
def delete_handover(item_id: int):
    db = SessionLocal()
    try:
        row = db.get(MillHandover, item_id)
        if not row:
            return error("交接班记录不存在", 404)
        db.delete(row)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
