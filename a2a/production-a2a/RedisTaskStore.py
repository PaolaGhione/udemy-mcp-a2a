import redis.asyncio as redis
from google.protobuf.json_format import MessageToJson, Parse

from a2a.server.context import ServerCallContext
from a2a.server.tasks.task_store import TaskStore
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse, Task
from a2a.utils.constants import DEFAULT_LIST_TASKS_PAGE_SIZE


class RedisTaskStore(TaskStore):
    """Task store that persists A2A tasks in Redis.

    In a2a-sdk 1.x a Task is a protobuf message (not a Pydantic model anymore),
    so we serialize it with protobuf's JSON helpers instead of model_dump_json().
    The store is shared by all the copies of the agent behind the load balancer.
    """

    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _key(task_id: str) -> str:
        return f"task:{task_id}"

    async def save(self, task: Task, context: ServerCallContext) -> None:
        await self.client.set(self._key(task.id), MessageToJson(task))

    async def get(self, task_id: str, context: ServerCallContext) -> Task | None:
        data = await self.client.get(self._key(task_id))
        if not data:
            return None
        return Parse(data, Task())

    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        await self.client.delete(self._key(task_id))

    async def list(self, params: ListTasksRequest, context: ServerCallContext) -> ListTasksResponse:
        # Required by the 1.x TaskStore interface. Simple version for the demo:
        # scan all the task keys, filter, sort by id and return the first page.
        tasks: list[Task] = []
        async for key in self.client.scan_iter(match="task:*"):
            data = await self.client.get(key)
            if not data:
                continue
            task = Parse(data, Task())
            if params.context_id and task.context_id != params.context_id:
                continue
            if params.status and task.status.state != params.status:
                continue
            tasks.append(task)

        tasks.sort(key=lambda t: t.id)
        page_size = params.page_size or DEFAULT_LIST_TASKS_PAGE_SIZE
        return ListTasksResponse(
            tasks=tasks[:page_size],
            total_size=len(tasks),
            page_size=page_size,
        )
