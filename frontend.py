from flask import Flask, render_template
from sqlalchemy import create_engine
from flask import request
import requests
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from PIL import Image
import json
from lxml import html
import re
import statsmodels.formula.api as smf
import statsmodels.api as sm
from collections import OrderedDict
import seaborn as sns
sns.set(style="whitegrid")
matplotlib.style.use(['seaborn-talk', 'seaborn-ticks', 'seaborn-whitegrid'])

app = Flask(__name__)

# The home page
@app.route('/')
def home():
    
    grade_list = [4]
    preparedness_list = [7]
    communication_list = [7]
    motivation_list = [7]
    challenging_list = [7]
    demanding_list = [7]
    interest_list = [7]
    overallinst_list = [7]
    overallcourse_list = [7]
    recommendation_list = [7]
    
    df = pd.DataFrame(OrderedDict({
        'expected_grade' : grade_list,
        'preparedness' : preparedness_list,
        'communication' : communication_list,
        'motivation' : motivation_list,
        'challenging' : challenging_list,
        'demanding' : demanding_list,
        'interest' : interest_list,
        'overall_instructor' : overallinst_list,
        'overall_course' : overallcourse_list,
        'recommendation_score' : recommendation_list
    }))
    
    #panos_home = 'static/panos_home.png'
    
    return render_template('/proj/index.html', scale_table = df.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]))#,panos_home=panos_home)

# Aggregate analysis page
@app.route('/agg_analysis')
def agg_analysis():
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    ##Average ratings by semester
    query = '''
    SELECT*
    FROM cfe
    '''
    
    df = pd.read_sql(query, con=engine)
    df.replace('', np.nan, inplace=True)
    df.dropna(axis=0, inplace=True)
    #df = df.drop(df[df.expected_grade > 4].index)
    df['response_rate'] = df['num_responses'] / df['students_registered']
    df['grade_over_challenging'] = df['expected_grade'] / df['challenging']
    df['grade_over_demanding'] = df['expected_grade'] / df['demanding']
    df['raw_overall_instructor']=df['overall_instructor']*df['num_responses']
    df['raw_challenging']=df['challenging']*df['num_responses']
    df['raw_demanding']=df['demanding']*df['num_responses']
    df['raw_grade']=df['expected_grade']*df['num_responses']
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS:')]
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS: DISCOU')]
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS')]
    df = df[~df['class_name'].str.contains('PROFESSIONAL RESP. & LEADERSHI')]

    pivot = pd.pivot_table(data = df,
                          index = 'semester',
                          values = ['num_responses','raw_overall_instructor','raw_challenging','raw_demanding','raw_grade'],
                          aggfunc = sum)
    df_ratings_by_sem = pd.DataFrame(pivot)
    df_ratings_by_sem['average_overall_instructor'] = df_ratings_by_sem['raw_overall_instructor']/df_ratings_by_sem['num_responses']
    df_ratings_by_sem['average_demanding'] = df_ratings_by_sem['raw_demanding']/df_ratings_by_sem['num_responses']
    df_ratings_by_sem['average_challenging'] = df_ratings_by_sem['raw_challenging']/df_ratings_by_sem['num_responses']
    df_ratings_by_sem['average_grade'] = df_ratings_by_sem['raw_grade']/df_ratings_by_sem['num_responses']
    df_ratings_by_sem=df_ratings_by_sem.drop(columns=['raw_challenging','raw_demanding','raw_overall_instructor','num_responses','raw_grade'])
    
    
    ##Average by semester plot
    image_filename = create_seaborn(df_ratings_by_sem, 'avg_sem') #create_plot(df, 'avg_sem')
    
    ##Average by professor - best and worst ranked profs
    pivot2 = pd.pivot_table(data = df,
                          index = 'prof_name',
                          values = ['num_responses','raw_overall_instructor','raw_challenging','raw_demanding', 'raw_grade'],
                          aggfunc = sum)
    df_prof = pd.DataFrame(pivot2)
    df_prof['average_overall_instructor'] = df_prof['raw_overall_instructor']/df_prof['num_responses']
    df_prof['average_demanding'] = df_prof['raw_demanding']/df_prof['num_responses']
    df_prof['average_challenging'] = df_prof['raw_challenging']/df_prof['num_responses']
    df_prof['average_grade'] = df_prof['raw_grade']/df_prof['num_responses']
    df_prof = df_prof.sort_values(by='average_overall_instructor', ascending=False).drop(df_prof[df_prof.num_responses < 20].index)
    df_prof=df_prof.drop(columns=['raw_challenging','raw_demanding','raw_overall_instructor','raw_grade'])
    df_best_profs = df_prof[:10]
    df_worst_profs = df_prof[-10:].sort_values(['average_overall_instructor'], ascending=True)
    
    ## Regression of prof overall rating against challenging+demanding+num responses
    regression = smf.ols(formula='average_overall_instructor~average_grade+average_demanding+average_challenging+num_responses', data=df_prof).fit()
    regression_table = regression.summary().__repr__()

    ## Scatterplot of overall rating vs challenging
    scatter_plot_prof = seaborn_scatter(df_prof, 'average_challenging', 'average_overall_instructor', 'prof_scatter')
    
    ## Easiness score vs overall rating
    df['raw_grade']=df['expected_grade']*df['num_responses']
    pivot_course= pd.pivot_table(data = df,
                          index = 'class_name',
                          values = ['num_responses','raw_overall_instructor','raw_challenging','raw_demanding','raw_grade'],
                          aggfunc = sum)
    df_course = pd.DataFrame(pivot_course)
    df_course['average_overall_instructor'] = df_course['raw_overall_instructor']/df_course['num_responses']
    df_course['average_demanding'] = df_course['raw_demanding']/df_course['num_responses']
    df_course['average_challenging'] = df_course['raw_challenging']/df_course['num_responses']
    df_course['average_grade']=df_course['raw_grade']/df_course['num_responses']
    df_course = df_course.drop(df_course[df_course.num_responses < 30].index).drop(columns=['raw_challenging','raw_demanding','raw_overall_instructor','raw_grade'])#,index=['BUSINESS & ITS PUBLICS:','BUSINESS & ITS PUBLICS: DISCOU','BUSINESS & ITS PUBLICS','PROFESSIONAL RESP. & LEADERSHI'])
    df_course['easiness_number']=df_course['average_grade']/(df_course['average_demanding']+df_course['average_challenging'])
    df_course2 = df_course[['easiness_number','average_overall_instructor']].sort_values(by='easiness_number', ascending=False)
    df_easy = df_course2.sort_values(['easiness_number'], ascending=False).head(10)
    df_hard = df_course2.sort_values(['easiness_number'], ascending=True).head(10)
    
    ## Scatter plot of easiness vs overall instructor
    joint_plot = seaborn_jointplot(df_course2, 'easiness_number', 'average_overall_instructor', 'jointplot')
    
    ## Joining with RMP - analyzing cfe results vs RMP
    query_rmp = '''
    select lname, fname, rmp_rating, rmp_difficulty
    from sterncfe.rmp;
    '''
    
    df_rmp = pd.read_sql(query_rmp, con=engine)
    df_rmp = df_rmp.rename(columns={'lname': 'prof_name'})
    
    pivot_prof = df_prof.pivot_table(index = 'prof_name')
    df_prof_new = pd.DataFrame(pivot_prof)
    
    df_cfermp = pd.merge(df_prof_new, df_rmp, on = 'prof_name', how = 'inner', sort = True)
    
    df_cfermp['rmp_rating'] = df_cfermp['rmp_rating'].astype('float')
    df_cfermp['rmp_difficulty'] = df_cfermp['rmp_difficulty'].astype('float')
    
    df_cfermp['cfe_rating/7'] = df_cfermp['average_overall_instructor'] / 7
    df_cfermp['rmp_rating/5'] = df_cfermp['rmp_rating'] / 5
    df_cfermp['cfe_difficulty/7'] = df_cfermp['average_challenging'] / 7
    df_cfermp['rmp_difficulty/5'] = df_cfermp['rmp_difficulty'] / 5
    df_cfermp['rating_difference'] = df_cfermp['cfe_rating/7'] - df_cfermp['rmp_rating/5']
    df_cfermp['difficulty_difference'] = df_cfermp['cfe_difficulty/7'] - df_cfermp['rmp_difficulty/5']
    
    df_joint_display = df_cfermp[['prof_name','fname','rating_difference','difficulty_difference',
                                  'cfe_rating/7','rmp_rating/5','cfe_difficulty/7',
                                  'rmp_difficulty/5']]
    
    #'cfe_rating_percentage','rmp_rating_percentage','cfe_difficulty_percentage','rmp_difficulty_percentage',
    
    con.close()
    return render_template('/proj/fun_facts.html', table=df_ratings_by_sem.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), image=image_filename, best_prof=df_best_profs.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), worst_prof=df_worst_profs.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), regression_table = regression_table, prof_scatter = scatter_plot_prof, table_easy=df_easy.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), table_hard=df_hard.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), jointplot=joint_plot, joint_display = df_joint_display.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]))

# Google visions data
@app.route('/google_vision')
def google_vision():
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
     ## Google facial api analytics
    
    query_goog = '''
    select*
    from facial
    '''
    
    df_goog = pd.read_sql(query_goog, con=engine)
    df_goog = df_goog.fillna(0)
    pivot_goog = df_goog.pivot_table(index = 'name',
                                    values = ['smile', 'elder', 'businessperson', 'spokesperson'])
    panos_search = (df_goog["name"] == "IPEIROTIS")
    foudy_search = (df_goog["name"] == "FOUDY")
    damodaran_search = (df_goog["name"] == "DAMODARAN")
    panos_url = df_goog[panos_search]['image_url'].iloc[0]
    foudy_url = df_goog[foudy_search]['image_url'].iloc[0]
    damodaran_url = df_goog[damodaran_search]['image_url'].iloc[0]
    
    panos_pic = show_image(panos_url, "PANOSDemo")
    foudy_pic = show_image(foudy_url, "FOUDYDemo")
    damodaran_pic = show_image(damodaran_url, "DAMODARANDemo")
    
    #panos_funny = 'static/panos_home.png'
    
    return render_template('/proj/google_vision.html', pivot_goog=pivot_goog.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), panos_pic=panos_pic, foudy_pic=foudy_pic, damodaran_pic=damodaran_pic)

# All data - full SQL table
@app.route('/alldata')
def alldata():
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    query = '''
    SELECT*
    FROM cfe
    '''
    
    table = con.execute(query)
    #df = pd.read_sql(query, con=engine)
    con.close()
    
    return render_template('/proj/alldata.html', table=table)

# Professor search search page, input prosessor name
@app.route('/profsearch')
def prof_search():
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    query = '''
    select distinct prof_name
    from cfe
    '''
    
    df = pd.read_sql(query, con=engine)
    
    #dup_list = ['BRENNER', 'BROWN', 'CHEN', 'COHEN', 'SMITH', 'WALKER']
    
    return render_template('/proj/search_profs.html')#, dup_list=dup_list)

# Professor ratings results page
@app.route('/profrating')
def profrating():

    prof_query = str(request.args.get('prof_query')).upper()
    
    dup_list = ['BRENNER', 'BROWN', 'CHEN', 'COHEN', 'SMITH', 'WALKER']
    
    if prof_query in dup_list:
        duplicate_notice = "This last name has duplicate entries. The results here are inaccurate. Please use Stern's CFE to search together with first name."
    else:
        duplicate_notice = ""
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    query_not_found = '''
    select distinct prof_name
    from cfe
    '''
    
    df_not_found = pd.read_sql(query_not_found, con=engine)
    
    prof_list = df_not_found['prof_name'].tolist()
    
    if prof_query not in prof_list:
        return render_template('/proj/prof_not_found.html')
    
    
    
    # NOT USED - older version of a summary table
    #query = '''
    #SELECT prof_name, COUNT(*) AS courses_taught, ROUND(AVG(overall_instructor),2) AS avg_overall, ROUND(AVG(expected_grade),2) AS avg_grade, ROUND(AVG(demanding),2) AS avg_demanding, ROUND(AVG(challenging),2) AS avg_challenging, ROUND(AVG(communication),2) AS avg_communication, ROUND(AVG(students_registered),2) AS avg_class_size
    #FROM cfe
    #WHERE prof_name = %s
    #GROUP BY prof_name
    #'''
    
    #df_top = pd.read_sql(query, con=engine, params={prof_query})
    #table = con.execute(query, (prof_query,))
    #df_top = df_top.drop(df_top[df_top.expected_grade > 4].index)
    #df_top = df_top.set_index('prof_name')
    
    
    # Arithmetic average summary table
    query = '''
    select*
    from cfe
    '''
    df_top = pd.read_sql(query, con=engine)
    df_top = df_top[~df_top['class_name'].str.contains('BUSINESS & ITS PUBLICS:')]
    df_top = df_top[~df_top['class_name'].str.contains('BUSINESS & ITS PUBLICS: DISCOU')]
    df_top = df_top[~df_top['class_name'].str.contains('BUSINESS & ITS PUBLICS')]
    df_top = df_top[~df_top['class_name'].str.contains('PROFESSIONAL RESP. & LEADERSHI')]
    pivot_top = df_top.pivot_table(index = 'prof_name',
                                  values = ['overall_instructor', 'expected_grade', 'demanding',
                                           'challenging', 'communication'])
    search_df = pivot_top.index.get_level_values('prof_name') == str(prof_query)
    df_top = pd.DataFrame(pivot_top[search_df])
    df_top = df_top[['overall_instructor', 'expected_grade', 'demanding',
                                           'challenging', 'communication']]
    
    # Prof trends analysis
    query2 = '''
    SELECT*
    FROM cfe
    '''
    
    #table = con.execute(query)
    #con.close()
    
    df = pd.read_sql(query2, con=engine)
    #df.replace('', np.nan, inplace=True)
    #df.dropna(axis=0, inplace=True)
    df = df.drop(df[df.expected_grade > 4].index)
    df['response_rate'] = df['num_responses'] / df['students_registered']
    df['grade_over_challenging'] = df['expected_grade'] / df['challenging']
    df['grade_over_demanding'] = df['expected_grade'] / df['demanding']
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS:')]
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS: DISCOU')]
    df = df[~df['class_name'].str.contains('BUSINESS & ITS PUBLICS')]
    df = df[~df['class_name'].str.contains('PROFESSIONAL RESP. & LEADERSHI')]
    
    pivot = pd.pivot_table(data = df,
                          index = ['prof_name','semester'],
                          values = ['expected_grade','recommendation_score', 'grade_over_challenging', 'demanding'])
    search = pivot.index.get_level_values('prof_name') == str(prof_query)
    #pivot[search]
    
    #manipulate pivot[search] after identifying prof, before plotting, to drop prof_name
    df_no_prof = pivot[search]
    df_no_prof = df_no_prof.reset_index()
    df_no_prof = df_no_prof.drop(columns=['prof_name'])
    df_no_prof = df_no_prof.set_index('semester')
    
    image_filename = create_seaborn(df_no_prof, (prof_query+' trend'))
    grade_chal_image = create_seaborn(df_no_prof['grade_over_challenging'], (prof_query+' grade'))
    
    # Regression analysis of profs
    prof_search = (df['prof_name'] == prof_query)
    prof_df = df[prof_search]
    reg_class = smf.ols(formula='overall_instructor~expected_grade+challenging+demanding', data=prof_df).fit()
    reg_personal = smf.ols(formula='overall_instructor~preparedness+communication+motivation+interest', data=prof_df).fit()
    
    reg_table_class = reg_class.summary().__repr__()
    reg_table_personal = reg_personal.summary().__repr__()
    
    # Weighted Average Table
    df['raw_overall_instructor']=df['overall_instructor']*df['num_responses']
    df['raw_grade']=df['expected_grade']*df['num_responses']
    df['raw_challenging']=df['challenging']*df['num_responses']
    df['raw_demanding']=df['demanding']*df['num_responses']
    df['raw_communication']=df['communication']*df['num_responses']
    pivot2 = pd.pivot_table(data = df,
                          index = 'prof_name',
                          values = ['num_responses','raw_overall_instructor','raw_grade','raw_demanding','raw_challenging',
                                    'raw_communication'],
                          aggfunc = sum)
    df_prof = pd.DataFrame(pivot2)
    df_prof['average_overall_instructor'] = df_prof['raw_overall_instructor']/df_prof['num_responses']
    df_prof['average_grade'] = df_prof['raw_grade']/df_prof['num_responses']
    df_prof['average_demanding'] = df_prof['raw_demanding']/df_prof['num_responses']
    df_prof['average_challenging'] = df_prof['raw_challenging']/df_prof['num_responses']
    df_prof['average_communication'] = df_prof['raw_communication']/df_prof['num_responses']
    df_prof = df_prof.sort_values(by='average_overall_instructor', ascending=False).drop(df_prof[df_prof.num_responses < 20].index)
    df_prof = df_prof.drop(columns=['raw_challenging','raw_demanding','raw_overall_instructor', 'raw_grade', 'raw_communication'])
    df_prof = df_prof.reset_index()
    search_prof = (df_prof['prof_name'] == prof_query)
    df_display = df_prof[search_prof]
    df_display = df_display.set_index('prof_name')
    
    # For displaying images
    query3 = '''
    select name, image_url
    from facial
    '''
    pd.set_option('display.max_colwidth', -1)
    imagedf = pd.read_sql(query3, con=engine)
    imagedf = imagedf.drop_duplicates()
    condition = (imagedf['name'] == prof_query)
    #imageurl = imagedf.loc[imagedf['name'] == prof_query, 'image_url'].iloc[0]
    image_url_df = imagedf.loc[imagedf['name'] == prof_query, 'image_url']
    if len(image_url_df)>0:
        imageurl = image_url_df.iloc[0]
    else:
        imageurl = "http://1.bp.blogspot.com/_ky1bf81QrMw/TUlSgZKc0vI/AAAAAAAABA0/K4ClLDL5opM/s1600/no_photo_male.jpg"
    
    
    # Data from google analytics
    query4 = '''
    select*
    from facial
    '''
    #pd.set_option('display.max_colwidth', -1)
    googledf = pd.read_sql(query4, con=engine)
    googledf = googledf.fillna(0)
    pivot_goog = googledf.pivot_table(index = 'name')
    search_goog = pivot_goog.index.get_level_values('name') == prof_query
    #pivot[search_goog]
    
    # Courses taught
    query5 = '''
    select prof_name, semester, class_name, course_num
    from cfe
    where prof_name = %s
    '''
    
    #table = con.execute(query, (prof_query,))
    df_courses = pd.read_sql(query5, con=engine, params={prof_query})
    #pivot_courses = df_courses.pivot_table(index = 'prof_name')
    
    
    
    #Comments from ratemyprofessors.com
    
    query6 = '''
    select lname, fname, rmp_rating, rmp_difficulty, tag_1, tag_2, tag_3, comment_1, comment_2, comment_3
    from rmp
    '''
    
    df_comments = pd.read_sql(query6, con=engine)
    if prof_query in df_comments['lname'].tolist():  
        comment_1 = df_comments.loc[df_comments['lname'] == prof_query, 'comment_1']
        comment_2 = df_comments.loc[df_comments['lname'] == prof_query, 'comment_2']
        comment_3 = df_comments.loc[df_comments['lname'] == prof_query, 'comment_3']
        comment1 = comment_1.iloc[0]
        comment2 = comment_2.iloc[0]
        comment3 = comment_3.iloc[0]
        search_rmp = (df_comments["lname"] == prof_query)
        df_rmp = df_comments[search_rmp].reset_index()[['lname','rmp_rating','rmp_difficulty','tag_1','tag_2','tag_3']]
    else:
        comment1 = "No Comments Found"
        comment2 = ""
        comment3 = ""
        df_rmp = pd.DataFrame()
    
    
    
    profile_picture = show_image(imageurl, (prof_query+' photo'))

    con.close()
    
    return render_template('/proj/profrating.html', prof_query=prof_query, table=df_top.to_html(classes = ["table-striped", "table", "table-bordered", "table-hover"]), table_goog=pivot_goog[search_goog].to_html(classes = ["table-striped", "table", "table-bordered","table-hover","table-sm"]), table_courses = df_courses.to_html(classes = ["table-striped", "table", "table-bordered","table-hover","table-sm"]), table2=pivot[search].to_html(classes = ["table-striped", "table", "table-bordered","table-hover","table-sm"]), image=image_filename, image_grade = grade_chal_image, profilepic=profile_picture, table_wtd=df_display.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), reg_class=reg_table_class, reg_personal=reg_table_personal, comment1=comment1, comment2=comment2, comment3=comment3, table_rmp=df_rmp.to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), duplicate_notice = duplicate_notice)
    #return prof_query

# Course search page, enter course name and metrics
@app.route('/coursesearch')
def course_search():
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    query = '''
    select distinct class_name
    from cfe
    '''
    
    df = pd.read_sql(query, con=engine)
    
    courses = df['class_name'].tolist()
    sorted_courses = sorted(courses)
    
    metrics = ['average_overall_instructor','average_grade','average_demanding','average_challenging','average_communication',
             'average_motivation','average_interest','average_preparedness']
    
    ratios = ['grade_over_challenging','grade_over_demanding',
             'overall_over_motivation','overall_over_communication','overall_over_preparedness','overall_over_interest']
    
    return render_template('/proj/course_search.html', courses = sorted_courses, metrics=metrics, ratios=ratios)    

# Course search results page
@app.route('/course_comparison')
def course_comparison():
    
    course_query = str(request.args.get('course_query')).upper()
    metric_query = str(request.args.get('metric_query'))
    ratio_query = str(request.args.get('ratio_query'))
    
    conn_string = 'mysql://{user}:{password}@{host}:{port}/{db}'.format(
        user='root',
        password='P5mwahopkq8FKqnD',
        host='35.236.242.29',
        port=3306,
        db='sterncfe')

    engine = create_engine(conn_string)
    con = engine.connect()
    
    query = '''
    SELECT*
    FROM cfe
    '''
    
    df = pd.read_sql(query, con=engine)
    #df.replace('', np.nan, inplace=True)
    #df.dropna(axis=0, inplace=True)
    
    ## Arithmetic average analytics - not used
    #df['response_rate'] = df['num_responses'] / df['students_registered']
    #df['grade_over_challenging'] = df['expected_grade'] / df['challenging']
    #df['grade_over_demanding'] = df['expected_grade'] / df['demanding']
    #df['overall_over_motivation'] = df['overall_instructor'] / df['motivation']
    #df['overall_over_preparedness'] = df['overall_instructor'] / df['preparedness']
    
    
    #pivot = pd.pivot_table(data = df,
                       #index = ['class_name', 'prof_name'],
                       #values = ['grade_over_challenging', 'grade_over_demanding', 'recommendation_score', 'overall_course', 'expected_grade', 'overall_over_motivation','overall_over_preparedness']
                      #)
    
    ## Weighted average analytics
    df['raw_overall_instructor']=df['overall_instructor']*df['num_responses']
    df['raw_grade']=df['expected_grade']*df['num_responses']
    df['raw_challenging']=df['challenging']*df['num_responses']
    df['raw_demanding']=df['demanding']*df['num_responses']
    df['raw_communication']=df['communication']*df['num_responses']
    df['raw_motivation']=df['motivation']*df['num_responses']
    df['raw_interest']=df['interest']*df['num_responses']
    df['raw_preparedness']=df['preparedness']*df['num_responses']
    
    pivot2 = pd.pivot_table(data = df,
                          index = ['class_name','prof_name'],
                          values = ['num_responses','raw_overall_instructor','raw_grade','raw_demanding','raw_challenging',
                                    'raw_communication','raw_motivation','raw_interest','raw_preparedness'],
                          aggfunc = sum)
    df_prof = pd.DataFrame(pivot2)
    df_prof['average_overall_instructor'] = df_prof['raw_overall_instructor']/df_prof['num_responses']
    df_prof['average_grade'] = df_prof['raw_grade']/df_prof['num_responses']
    df_prof['average_demanding'] = df_prof['raw_demanding']/df_prof['num_responses']
    df_prof['average_challenging'] = df_prof['raw_challenging']/df_prof['num_responses']
    df_prof['average_communication'] = df_prof['raw_communication']/df_prof['num_responses']
    df_prof['average_motivation'] = df_prof['raw_motivation']/df_prof['num_responses']
    df_prof['average_interest'] = df_prof['raw_interest']/df_prof['num_responses']
    df_prof['average_preparedness'] = df_prof['raw_preparedness']/df_prof['num_responses']
    df_prof['grade_over_challenging'] = df_prof['average_grade']/df_prof['average_challenging']
    df_prof['grade_over_demanding'] = df_prof['average_grade']/df_prof['average_demanding']
    df_prof['overall_over_motivation'] = df_prof['average_overall_instructor']/df_prof['average_motivation']
    df_prof['overall_over_communication'] = df_prof['average_overall_instructor']/df_prof['average_communication']
    df_prof['overall_over_preparedness'] = df_prof['average_overall_instructor']/df_prof['average_preparedness']
    df_prof['overall_over_interest'] = df_prof['average_overall_instructor']/df_prof['average_interest']
    df_prof = df_prof.sort_values(by='average_overall_instructor', ascending=False)
    df_prof = df_prof.drop(columns=['raw_challenging','raw_demanding','raw_overall_instructor', 'raw_grade', 'raw_communication','raw_motivation','raw_interest','raw_preparedness'])
    #df_prof = df_prof.reset_index()
    
    pivot_metric=df_prof.pivot_table(index=['class_name', 'prof_name'],
                             values=['average_overall_instructor','average_grade','average_demanding','average_challenging',
                                     'average_communication','average_motivation','average_interest','average_preparedness'])
    column_order = ['average_overall_instructor','average_grade','average_demanding','average_challenging',
                                     'average_communication','average_motivation','average_interest','average_preparedness']
    pivot_metric = pivot_metric.reindex(column_order, axis=1)
    
    pivot_ratio=df_prof.pivot_table(index=['class_name', 'prof_name'],
                             values=['grade_over_challenging','grade_over_demanding','overall_over_motivation',
                                     'overall_over_communication','overall_over_preparedness','overall_over_interest'])
    
    metric_search = pivot_metric.index.get_level_values('class_name') == course_query
    ratio_search = pivot_ratio.index.get_level_values('class_name') == course_query
    #pivot[search].sort_values(by='expected_grade', ascending=False)
    
    winner_metric= pivot_metric[metric_search].sort_values(by=metric_query, ascending=False).head(1).index.get_level_values('prof_name')[0]
    winner_ratio = pivot_ratio[ratio_search].sort_values(by=ratio_query, ascending=False).head(1).index.get_level_values('prof_name')[0]
    
    query1 = '''
    select name, image_url
    from facial
    '''
    pd.set_option('display.max_colwidth', -1)
    imagedf = pd.read_sql(query1, con=engine)
    imagedf = imagedf.drop_duplicates()
    
    #if(isinstance(imagedf.loc[imagedf['name'] == winner, 'image_url'].iloc[0], str)):
    metric_image_url_df = imagedf.loc[imagedf['name'] == winner_metric, 'image_url']
    if len(metric_image_url_df)>0:
        metric_imageurl = metric_image_url_df.iloc[0]
    else:
        metric_imageurl = "http://1.bp.blogspot.com/_ky1bf81QrMw/TUlSgZKc0vI/AAAAAAAABA0/K4ClLDL5opM/s1600/no_photo_male.jpg"
        
    ratio_image_url_df = imagedf.loc[imagedf['name'] == winner_ratio, 'image_url']
    if len(ratio_image_url_df)>0:
        ratio_imageurl = ratio_image_url_df.iloc[0]
    else:
        ratio_imageurl = "http://1.bp.blogspot.com/_ky1bf81QrMw/TUlSgZKc0vI/AAAAAAAABA0/K4ClLDL5opM/s1600/no_photo_male.jpg"
        
    metric_winner_picture = show_image(metric_imageurl, (winner_metric+'metric-win-photo'))
    ratio_winner_picture = show_image(ratio_imageurl, (winner_ratio+'ratio-win-photo'))
    
    query2 = '''
    select c.prof_name, c.class_name, c.overall_instructor, c.overall_course, c.expected_grade, c.communication, c.motivation, c.interest, c.challenging, c.demanding, c.recommendation_score, f.smile, f.elder, f.businessperson, f.spokesperson
    from cfe c inner join facial f on c.prof_name = f.name
    '''
    regression_df = pd.read_sql(query2, con=engine)
    regression_df = regression_df.fillna(0)
    search_reg = (regression_df["class_name"] == course_query)
    
    if regression_df[search_reg].empty == True:
        regression_table_all = ""
        regression_table_cfe = ""
        regression_table_google = ""

    else:
        
        regression_all = smf.ols(formula='overall_course~smile+elder+businessperson+spokesperson+expected_grade+challenging+demanding+communication+motivation+interest', data=regression_df[search_reg]).fit()
        regression_table_all = regression_all.summary().__repr__()#._repr_html_()

        regression_cfe = smf.ols(formula='overall_course~expected_grade+challenging+demanding+communication+motivation+interest', data=regression_df[search_reg]).fit()
        regression_table_cfe = regression_cfe.summary().__repr__()#._repr_html_()

        regression_google = smf.ols(formula='overall_course~smile+elder+businessperson+spokesperson', data=regression_df[search_reg]).fit()
        regression_table_google = regression_google.summary().__repr__()#._repr_html_()
    
    
    con.close()
    
    return render_template('/proj/courserating.html', metric_table=pivot_metric[metric_search].sort_values(by=metric_query, ascending=False).to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), ratio_table=pivot_ratio[ratio_search].sort_values(by=ratio_query, ascending=False).to_html(classes = ["table-striped", "table", "table-bordered","table-hover", "table-sm"]), metric_winnerpic = metric_winner_picture,ratio_winnerpic = ratio_winner_picture, winner_ratio=winner_ratio, winner_metric=winner_metric,course_query = course_query, metric_query = metric_query, ratio_query = ratio_query, regression_table_all=regression_table_all, regression_table_google=regression_table_google, regression_table_cfe=regression_table_cfe)

def create_plot(df, plot_name):
    plot = df.plot()
    filename = 'static/plot-'+plot_name+ '.png'
    fig = plot.get_figure()
    fig.savefig(filename)
    fig.clear()
    # Return back the name of the image file
    return filename

def create_seaborn(df, plot_name):
    #plt.figure()
    plot = sns.lineplot(data=df,palette="tab10", linewidth=2.5)
    plt.xticks(rotation=45)
    plt.rcParams['figure.figsize'] = (10, 20)
    filename = 'static/plot-'+plot_name+ '.png'
    fig = plot.get_figure()
    #fig.savefig(filename)
    fig.savefig(filename, bbox_inches='tight')
    fig.clear()
    return filename

def seaborn_scatter(df, x, y, plot_name):
    plot = sns.regplot(x = x, y = y, data=df, marker="+")
    filename = 'static/plot-'+plot_name+ '.png'
    fig = plot.get_figure()
    fig.savefig(filename, bbox_inches='tight')
    fig.clear()
    return filename

def seaborn_jointplot(df, x, y, plot_name):
    sns.set(style="ticks")
    #plt.figure()
    joint_plot = sns.jointplot(x=x, y=y, kind="hex", color="#4CB391", data=df)
    filename = 'static/plot-'+plot_name+ '.png'
    joint_plot.savefig(filename)
    plt.clf()
    return filename
    
def show_image(url, file_name):
    r = requests.get(url, allow_redirects=True)
    open(('static/'+file_name+'.png'), 'wb').write(r.content)
    filename = 'static/'+file_name+'.png'
    return filename
    
app.run(host='0.0.0.0', port=5000, debug=True)