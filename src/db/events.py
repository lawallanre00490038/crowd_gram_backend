from sqlalchemy import event, update, select
from src.db.models import ReviewerAllocation, Submission, ProjectAllocation, Task


def _cascade_status(connection, submission_id: str, new_status: str):
    """
    Helper to cascade status to Submission, ProjectAllocation, and Task.
    """
    # 1️⃣ Update Submission
    connection.execute(
        update(Submission.__table__)
        .where(Submission.id == submission_id)
        .values(status=new_status)
    )

    # 2️⃣ Get ProjectAllocation (assignment) linked to this submission
    result = connection.execute(
        select(Submission.assignment_id).where(Submission.id == submission_id)
    )
    assignment_id_row = result.first()
    if not assignment_id_row or not assignment_id_row[0]:
        return
    assignment_id = assignment_id_row[0]

    # 3️⃣ Update ProjectAllocation
    connection.execute(
        update(ProjectAllocation.__table__)
        .where(ProjectAllocation.id == assignment_id)
        .values(status=new_status)
    )

    # 4️⃣ Get Task ID linked to the allocation
    result_task = connection.execute(
        select(ProjectAllocation.task_id).where(ProjectAllocation.id == assignment_id)
    )
    task_row = result_task.first()
    if not task_row or not task_row[0]:
        return
    task_id = task_row[0]

    # 5️⃣ Update Task
    connection.execute(
        update(Task.__table__)
        .where(Task.id == task_id)
        .values(status=new_status)
    )


# ----------------------------
# Trigger on INSERT
# ----------------------------
@event.listens_for(ReviewerAllocation, "after_insert")
def reviewer_allocation_insert(mapper, connection, target):
    _cascade_status(connection, target.submission_id, target.status)


# ----------------------------
# Trigger on UPDATE
# ----------------------------
@event.listens_for(ReviewerAllocation, "after_update")
def reviewer_allocation_update(mapper, connection, target):
    _cascade_status(connection, target.submission_id, target.status)
