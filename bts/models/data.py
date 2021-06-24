import pandas as pd
import boto3
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from ..utils import add_subplot
from collections import namedtuple

gaussian = namedtuple('Gaussian', ['mean', 'var'])
gaussian.__repr__ = lambda t: '𝒩(μ={:.3f}, 𝜎²={:.3f})'.format(t[0], t[1])

gaussian_linear = namedtuple('Gaussian', ['mu', 'beta', 'sigma'])
gaussian_linear.__repr__ = lambda t: '𝒩(μ={:.3f}, β={:.3f}, 𝜎²={:.3f})'.format(t[0], t[1], t[2])

class Data():
    
    def __init__(self, bucket, prefix, last_n_days=30):
        self.last_n_days = last_n_days
        self.bucket = bucket
        self.prefix = prefix
        self.unique_attrs = ['linename', 'subtrackname', 'Aligned Chainage', 'vehicle']
        self.useful_cols = ['linename', 'subtrackname', 'km', 'vehicle', 'datetime',
                            'acc', 'lat_jerk', 'lon_jerk', 'gauge', 'bolaccy', 'Aligned Chainage']
        self.df_raw = None
        self.df_processed = None
        self.df_result = None
        self.dates = []
        self.files = []
        self._get_path_list()
        
    def _get_path_list(self):
        s3 = boto3.resource('s3', region_name='ap-east-1')
        objs = list(s3.Bucket(self.bucket).objects.filter(Prefix=self.prefix))
        for i in range(1, len(objs)):
            self.files.append(objs[i].key)
            self.dates.append(objs[i].key.rsplit('/',4)[3].rsplit('.',2)[0])
        
    def _get_raw_generator(self):
        for date in self.dates[-self.last_n_days:]:
            df = pd.read_parquet(f's3://{self.bucket}/{self.prefix}{date}.parquet', columns=self.useful_cols)
            yield df
            
    def _get_max_sub_df(self, df, attr):
        attr_max = df[attr].value_counts().index[0]
        mask = df[attr] == attr_max
        return df[mask]
    
    @classmethod
    def get_one_sample(cls, bucket, prefix):       
        data = cls(bucket, prefix, 1)
        df = pd.read_parquet(f's3://{data.bucket}/{data.prefix}{data.dates[-1]}.parquet')
        return df

    @staticmethod
    def check_na(df, threshold=0.3):       
        df_na = df.isna().sum()/df.shape[0]
        return df_na[df_na>=threshold]
            
    def get_raw_generator(self):
        self.df_raw = pd.concat(list(self._get_raw_generator()))
        self.df_processed = self.df_raw
    
    def get_example(self):
        for attr in self.unique_attrs:
            self.df_processed = self._get_max_sub_df(self.df_processed, attr)
        
    def preprocessing(self):
        self.df_processed = self.df_processed.drop_duplicates('datetime').sort_values(by='datetime')
        #self.df_processed['gauge'] = self.df_processed['gauge'].interpolate(limit=2)
        
    def scatter_plot_chainage_hue(self, chainage=2.1, direction='Down'):            
        mask1 = self.df_processed['Aligned Chainage'] == chainage
        mask2 = self.df_processed['subtrackname'].str.contains(direction)
        df = self.df_processed[mask1&mask2]
        fig, axes = plt.subplots(2,3, figsize=(16, 8))
        fig.suptitle(f'chainage={chainage}, direction={direction}')
        sns.scatterplot(data=df, hue='km', x='datetime', y='acc', ax=axes[0, 0])#.set_title('acc')
        sns.scatterplot(data=df, hue='km', x='datetime', y='bolaccy', ax=axes[0, 1])#.set_title('bolaccy')
        sns.scatterplot(data=df, hue='km', x='datetime', y='gauge', ax=axes[0, 2])#.set_title('gauge')
        sns.scatterplot(data=df, hue='vehicle', x='datetime', y='acc', ax=axes[1, 0])#.set_title('acc')
        sns.scatterplot(data=df, hue='vehicle', x='datetime', y='bolaccy', ax=axes[1, 1])#.set_title('bolaccy')
        sns.scatterplot(data=df, hue='vehicle', x='datetime', y='gauge', ax=axes[1, 2])#.set_title('gauge')
        fig.autofmt_xdate()
        plt.show()
            
    def sub_df(self, chainage=2.1, direction='Down', target='gauge'):
        mask1 = self.df_processed['Aligned Chainage'] == chainage
        mask2 = self.df_processed['subtrackname'].str.contains(direction)
        df = self.df_processed[mask1&mask2]
        df = df[['datetime', target]]
        df = df.set_index('datetime')
        return df
    
#class Sample():
#    
#    def __init__(self, N=50, sp_loc=0.2, mu_1=1440, mu_2=1445, beta_1=0.03, beta_2=0.1, sigma_1=0.3, sigma_2=0.6):
#        self.N = N
#        self.sp_loc = sp_loc
#        self.left_glm = gaussian_linear(mu_1, beta_1, sigma_1)
#        self.right_glm = gaussian_linear(mu_2, beta_2, sigma_2)
#        self.generate()
#
#    def generate(self):
#        '''
#        sp_loc: switchpoint location
#        x_1 vs x_2: before vs after switchpoint
#        '''
#        sp = int(self.N*self.sp_loc)
#        t = np.arange(0, self.N)
#        eps_1 = np.random.normal(0, self.left_glm.sigma, sp)
#        eps_2 = np.random.normal(0, self.right_glm.sigma, self.N-sp)
#        y_1 = self.left_glm.mu+self.left_glm.beta*t[:sp] + eps_1
#        y_2 = self.right_glm.mu+self.right_glm.beta*(t[sp:]-sp) + eps_2
#        y = np.concatenate((y_1, y_2))
#        self.y = y
#        self.t = t
#                           
#    def plot(self, fig=None):   
#        if fig is None:
#            fig = plt.figure(figsize=(18, 1))
#        ax = add_subplot()
#        ax.scatter(x=self.t, y=self.y)
#        plt.ylabel('y')
#        plt.xlabel('time')
#        fig.tight_layout()        

#class Sample():
#    
#    def __init__(self, N=50, mu=1440, beta=0.03, sigma=0.3):
#        self.N = N
#        self.glm = gaussian_linear(mu, beta, sigma)
#        #self.definition()
#
#    def definition(self):
#        t = np.arange(0, self.N)
#        eps = np.random.normal(0, self.glm.sigma, self.N)
#        y = self.glm.mu + self.glm.beta*t + eps
#        self.y = y
#        self.t = t
#        return np.array([y, t])
#        
#    def __add__(self, other):
#        return AddSample(self, other)
#                           
#    def plot(self, fig=None):   
#        
#        if fig is None:
#            fig = plt.figure(figsize=(18, 1))
#        ax = add_subplot()
#        ax.scatter(x=self.t, y=self.y)
#        plt.ylabel('y')
#        plt.xlabel('time')
#        fig.tight_layout() 
#
#class AddSample(Sample):
#    def __init__(self, left, right):
#        self.left = left
#        self.right = right
#        super().__init__()
#        self.definition()
#
#    def definition(self, *args, **kwargs):
#        left = self.left.definition(*args, **kwargs)
#        right = self.right.definition(*args, **kwargs)
#        
#        y = np.concatenate([left[0], right[0]])
#        t = np.concatenate([left[1], right[1]+left[1][-1]+1])
#        self.y = y
#        self.t = t
#        
#        return np.array([y, t])
#
#    def plot(self, *args, **kwargs):
#        left = self.left.plot(*args, **kwargs)
#        right = self.right.plot(*args, **kwargs)
#        return left + right
#
#    def __repr__(self):
#        return (
#            f"AddSample( \n"
#            f"    left={self.left} \n"
#            f"    right={self.right} \n"
#            f")"
#        )
    
class Sample():
    
    def __init__(self, N=50, mu=1440, beta=0.03, sigma=0.3):
        self.N = N
        self.glm = gaussian_linear(mu, beta, sigma)
        self.generate()

    def generate(self):
        t = np.arange(0, self.N)
        eps = np.random.normal(0, self.glm.sigma, self.N)
        y = self.glm.mu + self.glm.beta*t + eps
        self.y = y
        self.t = t
        
    def __add__(self, other):
        return AddSample(self, other)
                           
    def plot(self, fig=None):   
        
        if fig is None:
            fig = plt.figure(figsize=(18, 1))
        ax = add_subplot()
        ax.scatter(x=self.t, y=self.y)
        plt.ylabel('y')
        plt.xlabel('time')
        fig.tight_layout() 
        
    def __repr__(self):
        return f'{self.glm} with N={self.N}'

class AddSample(Sample):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        super().__init__()
        self.generate()

    def generate(self, *args, **kwargs):        
        y = np.concatenate([self.left.y, self.right.y])
        t = np.concatenate([self.left.t, self.right.t+self.left.t[-1]+1])
        self.y = y
        self.t = t

    def __repr__(self):
        return (
            f"AddSample( \n"
            f"    left={self.left} \n"
            f"    right={self.right} \n"
            f")"
        )