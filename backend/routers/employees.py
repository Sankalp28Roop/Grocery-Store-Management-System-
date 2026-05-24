"""
routers/employees.py — Employee shift logging, payroll calculation, and scheduling.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user, pagination, require_manager_or_above
from backend.models import EmployeeShift, User
from backend.schemas import ShiftCreate, ShiftResponse, ShiftUpdate

router = APIRouter(prefix="/api/employees", tags=["Employees & Payroll"])


def _enrich_shift(shift: EmployeeShift) -> dict:
    """Attach computed hours_worked and gross_pay to shift dict."""
    data = {c.name: getattr(shift, c.name) for c in shift.__table__.columns}
    if shift.clock_out and shift.clock_in:
        delta = shift.clock_out - shift.clock_in
        hours = round(delta.total_seconds() / 3600, 2)
        data["hours_worked"] = hours
        data["gross_pay"] = round(hours * shift.hourly_rate, 2)
    else:
        data["hours_worked"] = None
        data["gross_pay"] = None
    return data


@router.get("/shifts", response_model=List[ShiftResponse])
def list_shifts(
    user_id: Optional[int] = Query(default=None),
    pag: dict = Depends(pagination),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List shifts. Non-managers can only view their own."""
    q = db.query(EmployeeShift)
    if current_user.role.value not in ("admin", "manager"):
        q = q.filter(EmployeeShift.user_id == current_user.id)
    elif user_id:
        q = q.filter(EmployeeShift.user_id == user_id)
    shifts = q.order_by(EmployeeShift.clock_in.desc()).offset(pag["skip"]).limit(pag["limit"]).all()
    return [_enrich_shift(s) for s in shifts]


@router.post("/shifts", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    employee = db.get(User, payload.user_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    shift = EmployeeShift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return _enrich_shift(shift)


@router.get("/shifts/{shift_id}", response_model=ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shift = db.get(EmployeeShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    if current_user.role.value not in ("admin", "manager") and shift.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return _enrich_shift(shift)


@router.patch("/shifts/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    shift = db.get(EmployeeShift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(shift, field, value)
    db.commit()
    db.refresh(shift)
    return _enrich_shift(shift)


@router.get("/payroll-summary", response_model=List[dict])
def payroll_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    """Aggregate gross pay per employee across all completed shifts."""
    employees = db.query(User).filter(User.role.in_(["cashier", "manager"])).all()
    results = []
    for emp in employees:
        shifts = db.query(EmployeeShift).filter(
            EmployeeShift.user_id == emp.id,
            EmployeeShift.clock_out != None,
        ).all()
        total_hours = sum(
            (s.clock_out - s.clock_in).total_seconds() / 3600
            for s in shifts if s.clock_out and s.clock_in
        )
        total_pay = sum(
            ((s.clock_out - s.clock_in).total_seconds() / 3600) * s.hourly_rate
            for s in shifts if s.clock_out and s.clock_in
        )
        avg_rating = (
            sum(s.performance_rating for s in shifts if s.performance_rating) /
            max(len([s for s in shifts if s.performance_rating]), 1)
        )
        results.append({
            "user_id": emp.id,
            "name": emp.name,
            "role": emp.role.value,
            "total_hours": round(total_hours, 2),
            "total_gross_pay": round(total_pay, 2),
            "shift_count": len(shifts),
            "avg_performance_rating": round(avg_rating, 2),
        })
    return results
