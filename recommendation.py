from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

def content_based_recommendation(article_title, data, cosine_sim, top_n=5):
    idx = data.index[data['title'] == article_title].tolist()
    if not idx:
        return []
    idx = idx[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]
    article_indices = [i[0] for i in sim_scores]
    return data.iloc[article_indices][['title', 'link']].to_dict(orient='records')

def collaborative_filtering_recommendation(user_id, interaction_df, user_similarity_df, top_n=5):
    similar_users = user_similarity_df[user_id].sort_values(ascending=False).drop(user_id)
    similar_users_articles = interaction_df.loc[similar_users.index]
    article_scores = similar_users_articles.T.dot(similar_users) / similar_users.sum()
    recommended_articles = article_scores[interaction_df.loc[user_id] == 0].sort_values(ascending=False).head(top_n)
    return recommended_articles.index.tolist()

def contextual_filtering(current_time_of_day, data, cosine_sim, top_n=5):
    filtered_data = data[data['time_of_day'] == current_time_of_day]
    if filtered_data.empty:
        return []
    recent_article_idx = filtered_data.index[-1]
    sim_scores = list(enumerate(cosine_sim[recent_article_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]
    article_indices = [i[0] for i in sim_scores]
    return filtered_data.iloc[article_indices][['title', 'link']].to_dict(orient='records')
