# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import task_manager

app = FastAPI()

class Task(BaseModel):
    temperature: float
    duration: int  # Duration in seconds

@app.post("/task/")
def create_task(task: Task, background_tasks: BackgroundTasks):
    task_manager.start_task(task.temperature, task.duration)
    background_tasks.add_task(task_manager.task_loop)
    return {"detail": "Task started"}

@app.get("/task/")
def get_current_task():
    if task_manager.current_task is None:
        raise HTTPException(status_code=404, detail="No current task")
    return {
        "temperature": task_manager.current_task.temperature,
        "duration": task_manager.current_task.duration,
        "start_time": task_manager.current_task.start_time
    }

@app.put("/task/")
def update_current_task(task: Task, background_tasks: BackgroundTasks):
    task_manager.update_task(task.temperature, task.duration)
    background_tasks.add_task(task_manager.task_loop)
    return {
        "temperature": task_manager.current_task.temperature,
        "duration": task_manager.current_task.duration,
        "start_time": task_manager.current_task.start_time
    }

@app.delete("/task/")
def delete_current_task():
    task_manager.stop_task()
    return {"detail": "Task stopped and deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
