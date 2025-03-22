# main.py
from fastapi import FastAPI, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.services.service_manager import ServiceManager, ServiceType
import tempfile
import os
import requests
import hashlib
from datetime import datetime, timedelta
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="健康知识助手")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务管理器
service_manager = ServiceManager()


# ------------------------ 请求体模型 ------------------------
class QueryRequest(BaseModel):
    query: str


class SwitchSessionRequest(BaseModel):
    session_id: str


class DeleteSessionRequest(BaseModel):
    session_id: str


class DepartmentRequest(BaseModel):
    department: str


class ServiceTypeRequest(BaseModel):
    service_type: str

# class LocationRequest(BaseModel):
#     latitude: float
#     longitude: float
#     radius: int = 5000  # 默认5公里范围内
#     keyword: str = "医院"  # 默认搜索医院
#
# class Hospital(BaseModel):
#     name: str
#     address: str
#     distance: str
#     latitude: float
#     longitude: float
#     phone: Optional[str] = None
#     type: Optional[str] = None  # 医院类型(综合医院、专科医院等)
#     rating: Optional[float] = None  # 评分
#
# class HospitalResponse(BaseModel):
#     hospitals: List[Hospital]
#     total: int
#
# # 做一个简易缓存
# cache = {}
# CACHE_EXPIRY = 7200
# def with_cache(func):
#     async def wrapper(request: LocationRequest):
#         # 生成缓存键
#         lat = round(request.latitude, 3)
#         lng = round(request.longitude, 3)
#         cache_key = f"{lat}_{lng}_{request.radius}_{request.keyword}"
#         cache_key = hashlib.md5(cache_key.encode()).hexdigest()
#
#         # 检查缓存
#         now = datetime.now()
#         if cache_key in cache:
#             cache_time, cache_data = cache[cache_key]
#             if now - cache_time < timedelta(seconds=CACHE_EXPIRY):
#                 logger.info(f"Cache hit for key: {cache_key}")
#                 return cache_data
#
#         # 调用原函数
#         result = await func(request)
#
#         # 更新缓存
#         cache[cache_key] = (now, result)
#
#         # 清理过期缓存（简单实现，实际应用可能需要更复杂的缓存管理）
#         expired_keys = [k for k, (t, _) in cache.items() if now - t > timedelta(seconds=CACHE_EXPIRY)]
#         for k in expired_keys:
#             del cache[k]
#
#         return result
#
#     return wrapper

# ------------------------ 服务类型管理接口 ------------------------
@app.get("/service/types")
async def get_service_types():
    """获取所有支持的服务类型"""
    return {"service_types": service_manager.get_service_types()}


@app.post("/service/switch")
async def switch_service_type(req: ServiceTypeRequest):
    """切换服务类型"""
    try:
        service_type = ServiceType(req.service_type)
        service_manager.switch_service_type(service_type)
        return {
            "status": "success",
            "service_type": service_type,
            "service_name": service_manager._get_service_name(service_type)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/service/active")
async def get_active_service_type():
    """获取当前活跃的服务类型"""
    service_type = service_manager.active_service_type
    return {
        "service_type": service_type,
        "service_name": service_manager._get_service_name(service_type)
    }


# ------------------------ 对话接口 ------------------------

@app.post("/chat")
async def chat_endpoint(req: QueryRequest):
    """处理用户提问"""
    try:
        response = service_manager.process_input(req.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理错误: {str(e)}")


# ------------------------ 图像处理接口 ------------------------
@app.post("/image/analyze")
async def analyze_image(
        file: UploadFile = None,
        image_url: Optional[str] = None,
        query: Optional[str] = None
):
    """处理用户上传的医疗图像或图像URL，并返回分析结果"""
    try:
        # 确保当前是医疗服务
        if service_manager.active_service_type != ServiceType.MEDICAL:
            service_manager.switch_service_type(ServiceType.MEDICAL)

        # 处理上传的文件或URL
        if file:
            # 保存上传的文件到临时目录
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, file.filename)

            with open(temp_file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            # 处理图像
            result = service_manager.process_image_input(temp_file_path, query)

            # 清理临时文件
            os.remove(temp_file_path)
            os.rmdir(temp_dir)

            return {"response": result}
        elif image_url:
            # 处理图像URL
            result = service_manager.process_image_input(image_url, query)
            return {"response": result}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供图像文件或图像URL"
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图像处理错误: {str(e)}")

# ------------------------ 科室管理接口（仅适用于医疗服务） ------------------------
@app.post("/session/set-department")
async def set_session_department(req: DepartmentRequest):
    """设置当前会话的建议科室"""
    try:
        service_manager.set_department(req.department)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------ 多会话管理接口 ------------------------
@app.get("/sessions")
async def get_all_sessions(service_type: Optional[str] = None):
    """获取所有会话信息"""
    try:
        # 如果指定了服务类型，切换到该服务类型
        if service_type:
            try:
                service_manager.switch_service_type(ServiceType(service_type))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"不支持的服务类型: {service_type}")

        return {"sessions": service_manager.get_all_session_titles()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/new")
async def create_new_session():
    """创建新会话并切换为当前活跃会话"""
    try:
        session_id = service_manager.create_and_switch_new_session()
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/switch")
async def switch_session(req: SwitchSessionRequest):
    """切换当前活跃会话"""
    try:
        service_manager.switch_session(req.session_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/delete")
async def delete_session(req: DeleteSessionRequest):
    """删除指定会话"""
    try:
        service_manager.delete_session(req.session_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/active")
async def get_active_session():
    """获取当前活跃会话信息"""
    try:
        return service_manager.get_active_session_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/messages")
async def get_messages(session_id: str):
    """获取特定会话的所有消息"""
    try:
        messages = service_manager.get_session_messages(session_id)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#------------------------ 地图接口 ---------------------------
# @app.post("/nearby_hospitals", response_model=HospitalResponse)
# @with_cache
# async def get_nearby_hospitals_amap(request: LocationRequest):
#     # 高德地图API密钥
#     amap_key: str = "150f8557934f1ba9369b7c30b568587f"
#
#     # 构造请求URL
#     url = "https://restapi.amap.com/v5/place/around"
#     params = {
#         "key": amap_key,
#         "location": f"{request.longitude},{request.latitude}",
#         "keywords": request.keyword,
#         "radius": request.radius,
#         "types": "090000",  # 医疗类
#         "sortrule": "distance",
#         "offset": request.max_results,
#         "page": 1,
#         "extensions": "all"
#     }
#
#     try:
#         logger.info(f"Requesting from AMap API with params: {params}")
#         response = requests.get(url, params=params)
#         result = response.json()
#
#         if result.get("status") != "1":
#             logger.error(f"AMap API error: {result}")
#             raise HTTPException(status_code=500, detail=f"高德API返回错误: {result.get('info')}")
#
#         pois = result.get("pois", [])
#         hospitals = []
#
#         for poi in pois:
#             # 计算距离
#             distance_str = f"{float(poi.get('distance', 0)) / 1000:.1f}km"
#
#             location = poi.get("location", "").split(",")
#             if len(location) == 2:
#                 lng, lat = float(location[0]), float(location[1])
#             else:
#                 lng, lat = 0, 0
#
#             hospitals.append(Hospital(
#                 name=poi.get("name", "未知医院"),
#                 address=poi.get("address", "地址未知"),
#                 distance=distance_str,
#                 latitude=lat,
#                 longitude=lng,
#                 phone=poi.get("tel"),
#                 type=poi.get("type").split(";")[0] if poi.get("type") else None,
#                 rating=float(poi.get("rating", 0)) if poi.get("rating") else None,
#                 images=poi.get("photos", [])[:3] if poi.get("photos") else None
#             ))
#
#         response_data = HospitalResponse(
#             hospitals=hospitals,
#             total=len(hospitals)
#         )
#
#         logger.info(f"Found {len(hospitals)} hospitals")
#         return response_data
#
#     except Exception as e:
#         logger.exception("Error when getting hospitals from AMap")
#         raise HTTPException(status_code=500, detail=f"获取附近医院失败: {str(e)}")

# ------------------------ 健康检查接口 ------------------------
@app.get("/")
async def root():
    return {"message": "健康知识助手正在运行"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)