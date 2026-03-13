import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_squared_error, accuracy_score, r2_score
from typing import Dict, List, Tuple, Union, Optional
from loguru import logger

class ModelTrainer:
    """
    机器学习模型训练引擎
    负责构建数据集、训练模型、评估模型
    """
    
    def __init__(self):
        self.models = {
            "Random Forest Regressor": RandomForestRegressor(n_estimators=100, random_state=42),
            "Linear Regression": LinearRegression(),
            "Random Forest Classifier": RandomForestClassifier(n_estimators=100, random_state=42),
            "Logistic Regression": LogisticRegression(random_state=42)
        }
        self.trained_model = None
        self.feature_names = []
        
    def prepare_dataset(self, df: pd.DataFrame, feature_cols: List[str], target_col: str, test_size: float = 0.2) -> Dict:
        """
        准备训练和测试数据集
        """
        try:
            # 确保列存在
            missing_cols = [c for c in feature_cols + [target_col] if c not in df.columns]
            if missing_cols:
                logger.error(f"DataFrame 缺少列: {missing_cols}")
                return {}

            # 清洗数据：去除包含 NaN 的行 (因子计算和 shift 产生的)
            data = df[feature_cols + [target_col]].dropna()
            
            if data.empty:
                logger.warning("数据清洗后为空，无法训练")
                return {}
            
            X = data[feature_cols]
            y = data[target_col]
            
            # 时间序列分割 (不应随机打乱)
            split_idx = int(len(data) * (1 - test_size))
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
            
            self.feature_names = feature_cols
            
            # 获取测试集的日期索引 (假设 df 有 trade_date 列或 index 是日期)
            test_dates = None
            if 'trade_date' in df.columns:
                test_dates = df.loc[X_test.index, 'trade_date'].values
            else:
                test_dates = df.index[split_idx:].values

            return {
                "X_train": X_train, "X_test": X_test,
                "y_train": y_train, "y_test": y_test,
                "test_dates": test_dates
            }
        except Exception as e:
            logger.error(f"数据集准备失败: {e}")
            return {}

    def train_model(self, X_train, y_train, model_name: str = "Random Forest Regressor", **kwargs) -> Dict:
        """
        训练模型
        """
        try:
            logger.info(f"开始训练模型: {model_name}, 数据集大小: {X_train.shape}")
            
            # 动态实例化模型，避免使用缓存的旧实例导致 AttributeError
            model = None
            
            if "Random Forest" in model_name:
                if "Regressor" in model_name:
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                else:
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                    
            elif "Linear Regression" in model_name:
                model = LinearRegression()
                
            elif "Logistic Regression" in model_name:
                model = LogisticRegression(random_state=42)
                
            elif "XGBoost" in model_name:
                try:
                    import xgboost as xgb
                    if "Regressor" in model_name:
                        model = xgb.XGBRegressor(n_estimators=100, random_state=42)
                    else:
                        model = xgb.XGBClassifier(n_estimators=100, random_state=42)
                except ImportError:
                    logger.warning("XGBoost 未安装，将回退到 Random Forest")
                    if "Regressor" in model_name:
                        model = RandomForestRegressor(n_estimators=100, random_state=42)
                    else:
                        model = RandomForestClassifier(n_estimators=100, random_state=42)

            if model is None:
                # Default fallback
                logger.warning(f"未知模型类型 {model_name}, 使用默认 Random Forest Regressor")
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            
            # 更新参数
            if kwargs:
                # 简单处理，只设置存在的参数
                valid_params = model.get_params()
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
                if filtered_kwargs:
                    model.set_params(**filtered_kwargs)
                
            model.fit(X_train, y_train)
            self.trained_model = model
            
            logger.success(f"模型 {model_name} 训练完成")
            return {"status": "success", "model": model}
            
        except Exception as e:
            logger.error(f"模型训练失败详情: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
            
    def evaluate_model(self, X_test, y_test) -> Dict:
        """
        评估模型性能
        """
        if not self.trained_model:
            return {"status": "error", "message": "模型未训练"}
            
        try:
            y_pred = self.trained_model.predict(X_test)
            
            # Determine task type
            is_classifier = isinstance(self.trained_model, (RandomForestClassifier, LogisticRegression))
            try:
                import xgboost as xgb
                if isinstance(self.trained_model, xgb.XGBClassifier):
                    is_classifier = True
            except ImportError:
                pass

            metrics = {}
            if is_classifier:
                metrics['accuracy'] = accuracy_score(y_test, y_pred)
            else:
                metrics['mse'] = mean_squared_error(y_test, y_pred)
                metrics['r2'] = r2_score(y_test, y_pred)
                
            # Calculate IC (Information Coefficient) for regression
            ic = 0.0
            if not is_classifier:
                df_res = pd.DataFrame({'pred': y_pred, 'true': y_test})
                ic = df_res.corr().iloc[0, 1]
            
            return {
                "status": "success",
                "metrics": metrics,
                "ic": ic,
                "y_pred": y_pred
            }
        except Exception as e:
            logger.error(f"评估失败: {e}")
            return {"status": "error", "message": str(e)}

    def save_model(self, filepath: str) -> bool:
        """保存模型到文件"""
        try:
            import joblib
            import os
            
            if not self.trained_model:
                logger.error("没有已训练的模型可保存")
                return False
                
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 保存模型和特征名
            save_data = {
                'model': self.trained_model,
                'feature_names': self.feature_names
            }
            joblib.dump(save_data, filepath)
            logger.info(f"模型已保存至: {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存模型失败: {e}")
            return False

    def load_model(self, filepath: str) -> bool:
        """从文件加载模型"""
        try:
            import joblib
            import os
            
            if not os.path.exists(filepath):
                logger.error(f"模型文件不存在: {filepath}")
                return False
                
            data = joblib.load(filepath)
            
            # 兼容性检查
            if isinstance(data, dict) and 'model' in data:
                self.trained_model = data['model']
                self.feature_names = data.get('feature_names', [])
            else:
                # 假设是直接保存的模型对象 (旧版本兼容)
                self.trained_model = data
                self.feature_names = [] # 无法恢复特征名
                
            logger.info(f"模型已加载: {filepath}")
            return True
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return False

    def predict(self, X) -> np.ndarray:
        """
        使用训练好的模型进行预测
        """
        if not self.trained_model:
            logger.error("模型未训练")
            return np.array([])
        
        try:
            return self.trained_model.predict(X)
        except Exception as e:
            logger.error(f"预测失败: {e}")
            return np.array([])

    @property
    def feature_importance(self) -> Dict[str, float]:
        """
        兼容属性访问特征重要性
        """
        df = self.get_feature_importance()
        if df.empty:
            return {}
        return dict(zip(df['feature'], df['importance']))

    def get_feature_importance(self) -> pd.DataFrame:
        """
        获取特征重要性
        """
        if not self.trained_model:
            return pd.DataFrame()
            
        try:
            if hasattr(self.trained_model, 'feature_importances_'):
                importances = self.trained_model.feature_importances_
                return pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': importances
                }).sort_values('importance', ascending=False)
            elif hasattr(self.trained_model, 'coef_'):
                importances = self.trained_model.coef_
                # Handle multi-class or single target
                if len(importances.shape) > 1:
                    importances = importances[0]
                return pd.DataFrame({
                    'feature': self.feature_names,
                    'importance': np.abs(importances)
                }).sort_values('importance', ascending=False)
            else:
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"获取特征重要性失败: {e}")
            return pd.DataFrame()
