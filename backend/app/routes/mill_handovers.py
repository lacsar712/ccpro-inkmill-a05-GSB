from datetime import date, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.mill import Mill
from app.models.mill_handover import HANDOVER_SLOTS, MillHandover
from app.serializers import mill_handover_json
from app.utils import error

bp = Blueprint("mill_handovers", __name__, url_prefix="/api/mill-handovers")


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _validate(body: dict) -> str | None:
    mill_id = int(body.get("millId") or 0)
    if mill_id <= 0:
        return "请选择研磨机"

    if _parse_date(str(body.get("shiftDate", ""))) is None:
        return "交接日期格式应为 YYYY-MM-DD"

    slot = str(body.get("slot", "")).strip()
    if slot not in HANDOVER_SLOTS:
        return "班次无效，应为 morning / afternoon / night"

    if not str(body.get("fromOperator", "")).strip():
        return "交班人不能为空"

    if not str(body.get("toOperator", "")).strip():
        return "接班人不能为空"

    db = SessionLocal()
    try:
        if not db.get(Mill, mill_id):
            return "研磨机不存在"
    finally:
        db.close()

    return None


@bp.get("")
@jwt_required()
def list_handovers():
    mill_id = request.args.get("millId", type=int)
    date_str = (request.args.get("date") or "").strip()

    shift_date = None
    if date_str:
        shift_date = _parse_date(date_str)
        if shift_date is None:
            return error("日期格式应为 YYYY-MM-DD", 400)

    db = SessionLocal()
    try:
        q = db.query(MillHandover)
        if mill_id:
            q = q.filter(MillHandover.mill_id == mill_id)
        if shift_date:
            q = q.filter(MillHandover.shift_date == shift_date)
        rows = q.order_by(MillHandover.shift_date.desc(), MillHandover.id.desc()).all()
        return jsonify([mill_handover_json(r) for r in rows])
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_handover():
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        mill = db.get(Mill, int(body["millId"]))
        row = MillHandover(
            mill_id=mill.id,
            shift_date=_parse_date(str(body["shiftDate"])),
            slot=str(body["slot"]).strip(),
            from_operator=str(body["fromOperator"]).strip(),
            to_operator=str(body["toOperator"]).strip(),
            mill_status_snapshot=mill.status,
            note=str(body.get("note", "")).strip() or None,
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该机台当日该班次已有交接记录", 400)
        db.refresh(row)
        return jsonify(mill_handover_json(row)), 201
    finally:
        db.close()


@bp.put("/<int:item_id>")
@jwt_required()
def update_handover(item_id: int):
    body = request.get_json(silent=True) or {}
    err = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        row = db.get(MillHandover, item_id)
        if not row:
            return error("交接记录不存在", 404)

        row.mill_id = int(body["millId"])
        row.shift_date = _parse_date(str(body["shiftDate"]))
        row.slot = str(body["slot"]).strip()
        row.from_operator = str(body["fromOperator"]).strip()
        row.to_operator = str(body["toOperator"]).strip()
        row.note = str(body.get("note", "")).strip() or None
        # mill_status_snapshot 保持创建时写入的值，不随编辑变化
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return error("该机台当日该班次已有交接记录", 400)
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
            return error("交接记录不存在", 404)
        db.delete(row)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
