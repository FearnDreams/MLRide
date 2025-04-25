"""
This module contains the ViewSets for dataset management functionality.
It provides API endpoints for managing datasets.
包含数据集管理功能的视图集，提供数据集管理的API端点。
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import csv
from io import StringIO
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from .models import Dataset, DatasetPreview
from .serializers import DatasetSerializer, DatasetPreviewSerializer
from rest_framework.exceptions import APIException
import chardet
from django.utils.encoding import escape_uri_path
import base64
import mimetypes

# 设置日志记录器
logger = logging.getLogger(__name__)

class DatasetViewSet(viewsets.ModelViewSet):
    """
    数据集视图集
    
    提供数据集的CRUD操作和特殊操作，如预览、下载等
    """
    serializer_class = DatasetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        获取查询集
        
        返回当前用户的数据集和公开的数据集
        """
        user = self.request.user
        return Dataset.objects.filter(
            Q(creator=user) | Q(visibility='public')
        ).order_by('-created')
    
    def perform_create(self, serializer):
        """
        创建数据集，设置创建者为当前用户
        """
        serializer.save(creator=self.request.user)
        
    @action(detail=False, methods=['get'])
    def public(self, request):
        """
        获取公开数据集列表
        """
        # 仅获取公开数据集
        datasets = Dataset.objects.filter(visibility='public').order_by('-created')
        serializer = self.get_serializer(datasets, many=True)
        return Response({
            "status": "success",
            "message": "获取公共数据集成功",
            "data": serializer.data
        })
        
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        下载数据集文件
        返回包含文件名和Base64编码文件内容的JSON响应
        """
        try:
            dataset = self.get_object() # 可能抛出 Http404
        except Exception as e: # 更广泛地捕获 get_object 可能的错误
             logger.error(f"获取数据集 {pk} 失败: {str(e)}")
             return Response({
                 "status": "error",
                 "message": "找不到指定的数据集"
             }, status=status.HTTP_404_NOT_FOUND)
        
        file_path = dataset.get_absolute_file_path()
        
        # 严格检查文件是否存在
        if not dataset.file or not file_path or not os.path.isfile(file_path): # 使用 isfile 更准确
            logger.error(f"下载失败：文件不存在或路径无效。数据集ID: {pk}, 路径: {file_path}")
            return Response({
                "status": "error",
                "message": "文件不存在或已被移除"
            }, status=status.HTTP_404_NOT_FOUND)
            
        logger.info(f"开始准备数据集下载数据: ID={pk}, 文件路径={file_path}")
        
        # 增加下载计数
        try:
            with transaction.atomic():
                ds_locked = Dataset.objects.select_for_update().get(pk=dataset.pk)
                ds_locked.downloads += 1
                ds_locked.save(update_fields=['downloads'])
            logger.info(f"数据集 {pk} 下载次数增加至: {ds_locked.downloads}")
        except Exception as e:
            logger.error(f"更新数据集 {pk} 下载次数失败: {str(e)}")
            # 即使计数失败，也继续尝试准备下载数据
            
        # 读取文件内容并进行Base64编码
        try:
            with open(file_path, 'rb') as f:
                file_content_binary = f.read()
            
            base64_content = base64.b64encode(file_content_binary).decode('utf-8')
            
            # 生成正确的文件名
            dataset_name = dataset.name
            file_extension = dataset.get_file_extension()
            new_file_name = f"{dataset_name}.{file_extension}"
            
            # 获取文件的 MIME 类型，供前端使用
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream' # 默认 MIME 类型
            
            logger.info(f"成功准备下载数据: 文件名='{new_file_name}', Content-Type={content_type}")
            
            # 返回JSON响应
            return Response({
                "status": "success",
                "message": "获取下载数据成功",
                "data": {
                    'file_name': new_file_name,
                    'file_content': base64_content, # Base64编码后的文件内容
                    'content_type': content_type # 文件 MIME 类型
                }
            }, status=status.HTTP_200_OK)

        except FileNotFoundError: 
            logger.error(f"下载失败：文件在读取时未找到。数据集ID: {pk}, 路径: {file_path}")
            return Response({
                "status": "error",
                "message": "文件在读取时丢失"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"准备下载数据时发生未知错误: {str(e)}", exc_info=True)
            return Response({
                "status": "error",
                "message": f"准备下载数据时发生服务器内部错误"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        预览数据集文件
        
        根据文件类型返回不同的预览内容, 采用统一的响应结构
        """
        try:
            dataset = self.get_object()
            
            if not dataset.preview_available:
                return Response({
                    "status": "error",
                    "message": "此数据集不支持预览",
                    "data": {"file_type": dataset.get_file_extension(), "error": "不支持预览此文件类型"}
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not dataset.file or not os.path.exists(dataset.get_absolute_file_path()):
                return Response({
                    "status": "error",
                    "message": "文件不存在",
                    "data": {"file_type": dataset.get_file_extension(), "error": "文件不存在或已被删除"}
                }, status=status.HTTP_404_NOT_FOUND)
            
            file_path = dataset.get_absolute_file_path()
            file_type = dataset.get_file_extension()
            
            # 记录预览请求信息
            logger.info(f"开始预览数据集文件: ID={dataset.id}, 名称='{dataset.name}', 类型={file_type}, 路径={file_path}")
            
            response_data = {"file_type": file_type, "error": None}  # 统一结构

            # 图片文件直接返回
            if dataset.is_image():
                try:
                    return FileResponse(open(file_path, 'rb'))
                except FileNotFoundError:
                    logger.error(f"预览图片失败：文件未找到 {file_path}")
                    response_data["error"] = "图片文件丢失"
                    return Response({
                        "status": "error",
                        "message": "图片文件丢失",
                        "data": response_data
                    }, status=status.HTTP_404_NOT_FOUND)

            # 根据文件类型获取预览数据
            if file_type == 'csv':
                preview_details = self._preview_csv(file_path)
                response_data.update(preview_details)

            elif file_type in ['xlsx', 'xls']:
                preview_details = self._preview_excel(file_path)
                response_data.update(preview_details)

            elif file_type == 'json':
                preview_details = self._preview_json(file_path)
                response_data.update(preview_details)

            elif file_type == 'txt':
                preview_details = self._preview_txt(file_path)
                response_data.update(preview_details)

            else:
                error_msg = f"不支持预览此类型的文件: {file_type}"
                logger.warning(f"{error_msg}, 数据集ID={dataset.id}")
                response_data["error"] = error_msg
                return Response({
                    "status": "error",
                    "message": error_msg,
                    "data": response_data
                }, status=status.HTTP_400_BAD_REQUEST)

            # 检查预览结果是否包含错误
            if response_data.get("error"):
                logger.warning(f"预览数据集时出现问题: {response_data['error']}, 数据集ID={dataset.id}")
                return Response({
                    "status": "warning",  # 使用warning而不是error, 因为预览部分成功
                    "message": f"预览数据集遇到问题: {response_data['error']}",
                    "data": response_data
                })

            # 预览成功
            logger.info(f"成功预览数据集: ID={dataset.id}, 类型={file_type}")
            return Response({
                "status": "success",
                "message": "预览数据集成功",
                "data": response_data
            })

        except Exception as e:
            logger.exception(f"预览数据集时出错: {str(e)}")
            return Response({
                "status": "error",
                "message": f"预览数据集时出错: {str(e)}",
                "data": {"file_type": getattr(dataset, 'file_type', 'unknown'), "error": str(e)}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _preview_csv(self, file_path, max_rows=100):
        """读取CSV文件，返回包含预览数据的字典，增加编码和分隔符处理的健壮性"""
        encoding = 'utf-8' # 默认编码
        delimiter = ',' # 默认分隔符
        detected_encoding = None
        detected_delimiter = None
        error_message = None

        try:
            # 1. 编码检测
            with open(file_path, 'rb') as f:
                sample = f.read(min(os.path.getsize(file_path), 10240)) # 读取最多10KB样本
            
            if sample: # 仅当样本不为空时检测
                result = chardet.detect(sample)
                detected_encoding = result.get('encoding', 'utf-8')
                confidence = result.get('confidence', 0)
                # 如果检测结果可信，则使用检测到的编码
                if detected_encoding and confidence > 0.7:
                    encoding = detected_encoding
                else:
                    encoding = 'utf-8' # 不可信则回退到UTF-8
                logger.info(f"检测到CSV文件 {os.path.basename(file_path)} 的编码: {encoding} (原始检测: {detected_encoding}, 置信度: {confidence})")
            else:
                logger.warning(f"CSV文件 {os.path.basename(file_path)} 样本为空，使用默认编码 UTF-8")
                encoding = 'utf-8'

            # 2. 分隔符检测 (在确定编码后进行)
            try:
                if sample:
                    # 尝试用确定的编码解码样本
                    decoded_sample = sample.decode(encoding, errors='replace')
                    # 忽略空行进行嗅探
                    non_empty_lines = "\n".join(line for line in decoded_sample.splitlines() if line.strip())
                    if non_empty_lines:
                        dialect = csv.Sniffer().sniff(non_empty_lines)
                        detected_delimiter = dialect.delimiter
                        # 如果检测到的分隔符是字母数字或奇怪的字符，则认为检测失败
                        if detected_delimiter.isalnum() or detected_delimiter in [' ', '\t', '\n', '\r']:
                             logger.warning(f"检测到不寻常的分隔符 '{detected_delimiter}'，回退到默认逗号 ','")
                             delimiter = ','
                        else:
                            delimiter = detected_delimiter
                    else:
                        logger.warning(f"解码后的CSV样本不包含非空行，使用默认分隔符','")
                        delimiter = ','
                else:
                     logger.warning(f"CSV样本为空，使用默认分隔符','")
                     delimiter = ','
            except (csv.Error, UnicodeDecodeError) as sniff_err:
                logger.warning(f"CSV分隔符检测失败 ({sniff_err})，使用默认分隔符','")
                delimiter = ','
            
            logger.info(f"CSV文件 {os.path.basename(file_path)} 使用分隔符: '{delimiter}' (原始检测: {detected_delimiter})")
            
            # 3. 使用pandas读取CSV文件
            try:
                df = pd.read_csv(
                    file_path, 
                    sep=delimiter,
                    encoding=encoding,
                    nrows=max_rows, 
                    na_values=['NA', '', 'NULL', 'null', 'NaN', 'nan'],
                    keep_default_na=True,
                    on_bad_lines='warn', # 警告坏行
                    engine='python', # Python引擎更灵活，但可能慢
                    escapechar='\\' # 添加转义字符处理，尝试解决 ' ' expected after '"'
                )
            # 4. 处理编码错误回退
            except UnicodeDecodeError as ude:
                logger.warning(f"使用编码 {encoding} 读取CSV失败: {ude}. 尝试使用UTF-8回退...")
                # 如果第一次尝试的不是UTF-8，则用UTF-8重试
                if encoding.lower() != 'utf-8':
                    encoding = 'utf-8'
                    logger.info(f"尝试使用 UTF-8 重新读取 CSV 文件 {os.path.basename(file_path)}")
                    df = pd.read_csv(
                        file_path, sep=delimiter, encoding=encoding, nrows=max_rows,
                        na_values=['NA', '', 'NULL', 'null', 'NaN', 'nan'], keep_default_na=True,
                        on_bad_lines='warn', engine='python', escapechar='\\'
                    )
                else:
                    # 如果已经是UTF-8还失败，则抛出错误
                    raise ude

            # 5. 处理数据和返回
            if df.empty:
                logger.warning(f"CSV文件 {os.path.basename(file_path)} 为空或无有效数据（使用编码: {encoding}, 分隔符: '{delimiter}'）")
                return {
                    'columns': [], 'rows': [], 'encoding': encoding, 'delimiter': delimiter,
                    'error': '文件为空或不包含有效数据'
                }
            
            df = df.replace({np.nan: None, pd.NaT: None})
            
            total_rows = -1
            try:
                # 重新打开文件计算总行数，确保使用最终确定的编码
                with open(file_path, 'r', encoding=encoding, errors='replace') as f_count:
                    total_rows = sum(1 for _ in f_count) - 1 # 减去表头 (假设有表头)
            except Exception as count_err:
                logger.warning(f"无法计算总行数: {str(count_err)}")
            
            return {
                'columns': df.columns.tolist(),
                'rows': df.values.tolist(),
                'total_rows_estimated': total_rows,
                'preview_rows': len(df),
                'encoding': encoding, # 返回最终使用的编码
                'delimiter': delimiter # 返回最终使用的分隔符
            }
                
        except pd.errors.EmptyDataError:
            error_message = '文件为空'
            logger.warning(f"预览CSV失败 ({file_path}): {error_message}")
        except (pd.errors.ParserError, csv.Error) as pe:
            error_message = f"文件解析错误 (可能是分隔符或引用问题): {pe}"
            logger.error(f"预览CSV失败 ({file_path}): {error_message}")
        except UnicodeDecodeError as ude:
            error_message = f"文件编码错误 (尝试使用 {encoding} 解码失败): {ude}"
            logger.error(f"预览CSV失败 ({file_path}): {error_message}")
        except FileNotFoundError:
            error_message = "文件未找到"
            logger.error(f"预览CSV失败 ({file_path}): {error_message}")
        except Exception as e:
            error_message = f"预览CSV时发生未知错误: {str(e)}"
            logger.exception(f"预览CSV失败 ({file_path}): {error_message}") # 使用exception记录完整traceback

        # 如果有错误发生，返回错误信息
        return {'columns': [], 'rows': [], 'encoding': encoding, 'delimiter': delimiter, 'error': error_message}
    
    def _preview_excel(self, file_path, max_rows=100):
        """读取Excel文件，返回包含预览数据的字典"""
        try:
            xlsx = pd.ExcelFile(file_path)
            sheet_names = xlsx.sheet_names
            sheets_preview = {}

            for sheet_name in sheet_names:
                df = pd.read_excel(xlsx, sheet_name=sheet_name, nrows=max_rows)

                # 处理NaN/NaT为None
                df = df.replace({np.nan: None, pd.NaT: None})
                df = df.astype(object) # 确保所有类型都可序列化

                sheets_preview[sheet_name] = {
                    'columns': df.columns.tolist(),
                    'rows': df.values.tolist(),
                    'preview_rows': len(df),
                }

            return {
                'sheet_names': sheet_names,
                'sheets_preview': sheets_preview
            }

        except Exception as e:
            logger.exception(f"预览Excel文件失败: {file_path} - {str(e)}")
            return {'sheet_names': [], 'sheets_preview': {}, 'error': f'无法解析Excel文件: {str(e)}'}
    
    def _preview_json(self, file_path, max_size_kb=1024): # 按大小限制，避免加载巨大JSON
        """读取JSON文件，返回包含预览数据的字典"""
        try:
            file_size = os.path.getsize(file_path)
            if file_size > max_size_kb * 1024:
                 return {'content': None, 'error': f'JSON文件过大 ({file_size / 1024:.1f} KB)，超过预览限制 ({max_size_kb} KB)'}

            # 尝试检测编码
            with open(file_path, 'rb') as f_detect:
                sample = f_detect.read(4096)
            detected_encoding = chardet.detect(sample).get('encoding', 'utf-8') or 'utf-8'


            with open(file_path, 'r', encoding=detected_encoding, errors='replace') as f:
                # 优化：对于大文件，可以考虑只读取一部分或使用流式解析器
                data = json.load(f)

            # JSON预览通常直接显示内容，不需要截断，因为大小已限制
            return {
                'content': data,
                'encoding': detected_encoding
            }
        except json.JSONDecodeError as json_err:
             logger.warning(f"Preview JSON failed: Invalid JSON format in {file_path}: {json_err}")
             return {'content': None, 'error': f'无效的JSON格式: {json_err}'}
        except Exception as e:
            logger.exception(f"预览JSON文件失败: {file_path} - {str(e)}")
            return {'content': None, 'error': f'无法读取JSON文件: {str(e)}'}
    
    def _preview_txt(self, file_path):
        """
        预览TXT文件内容
        
        Args:
            file_path (str): TXT文件路径
            
        Returns:
            dict: 包含TXT预览数据的字典，包括行内容和编码信息
        """
        try:
            # 读取文件头部进行编码检测
            sample_size = 10240  # 读取前10KB用于检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read(sample_size)
            
            # 使用chardet检测文件编码
            detection = chardet.detect(raw_data)
            encoding = detection['encoding'] if detection['confidence'] > 0.7 else 'utf-8'
            logger.info(f"TXT文件编码检测结果: {detection}")
            
            # 读取文件内容（限制行数）
            max_lines = 100
            lines = []
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip('\n'))
            
            # 估计总行数
            total_lines = 0
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    total_lines = sum(1 for _ in f)
            except Exception as count_err:
                logger.warning(f"无法计算总行数: {str(count_err)}")
                total_lines = len(lines) if len(lines) < max_lines else -1
            
            # 返回与前端预期格式一致的结构
            return {
                'content': '\n'.join(lines),
                'encoding': encoding,
                'confidence': detection['confidence'],
                'line_count': len(lines),
                'total_lines': total_lines,
                'is_truncated': len(lines) >= max_lines
            }
        except Exception as e:
            logger.error(f"TXT文件预览失败: {e}", exc_info=True)
            return {
                'content': '',
                'error': f"无法预览TXT文件: {str(e)}"
            }
