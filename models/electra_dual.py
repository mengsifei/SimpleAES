from torch.nn import LayerNorm
import math
import torch.nn.functional as F
from transformers import ElectraModel
import torch.nn as nn
import torch
from models.poolings import *

class CrossAttention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.query = nn.Linear(hidden_size, hidden_size)
        self.key = nn.Linear(hidden_size, hidden_size)
        self.value = nn.Linear(hidden_size, hidden_size)
        self.scale = math.sqrt(hidden_size)
        self.norm = LayerNorm(hidden_size)

    def forward(self, queries, keys, values, mask=None):
        # Ensure queries, keys, values are 3D tensors; [batch, seq_len, features]
        Q = self.query(queries).unsqueeze(1)  # [batch, 1, features]
        K = self.key(keys).unsqueeze(2)       # [batch, features, 1]
        V = self.value(values)                # [batch, features]
        # Batch matrix multiplication, broadcasting over the middle dimension
        attention_scores = torch.bmm(Q, K) / self.scale  # [batch, 1, 1]
        if mask is not None:
            attention_scores = attention_scores.masked_fill(mask == 0, float('-inf'))

        attention_probs = F.softmax(attention_scores, dim=-1)  # [batch, 1, 1]
        context = torch.bmm(attention_probs, V.unsqueeze(1)).squeeze(1)  # [batch, features]
        context = self.norm(context)
        return context


class ResponsePromptAttention(nn.Module):
    def __init__(self, hidden_size):
        super(ResponsePromptAttention, self).__init__()
        self.scale = math.sqrt(hidden_size)
        self.W_q = nn.Linear(hidden_size, hidden_size, bias=False)
        self.W_k = nn.Linear(hidden_size, hidden_size, bias=False)
        self.W_v = nn.Linear(hidden_size, hidden_size, bias=False)

    def forward(self, responses, prompts):
        Q = self.W_q(responses)  # [batch_size, hidden_size]
        K = self.W_k(prompts)    # [batch_size, hidden_size]
        V = self.W_v(prompts)    # [batch_size, hidden_size]

        # Transpose for batch matrix multiplication to shape [batch_size, 1, hidden_size]
        attention_logits = torch.bmm(Q.unsqueeze(1), K.unsqueeze(2)) / self.scale
        attention_weights = F.softmax(attention_logits, dim=-1)  # Squeeze to remove singular dimensions

        # Attention output vector [batch_size, hidden_size]
        attention_output = torch.bmm(attention_weights, V.unsqueeze(1)).squeeze(1)
        return attention_output



class CustomELECTRA(nn.Module):
    def __init__(self, hidden_size=256, hidden_dropout_prob=0.2):
        super(CustomELECTRA, self).__init__()
        self.electra = ElectraModel.from_pretrained('google/electra-small-discriminator')
        self.response_prompt_attention = ResponsePromptAttention(hidden_size)
        self.pooler = MeanPooling()
        self.dropout = nn.Dropout(hidden_dropout_prob)
        self.out = nn.Linear(2 * hidden_size, 4)  # Adjusted for concatenated output

    def forward(self, essay_input_ids, essay_attention_mask, essay_token_type_ids, topic_input_ids, topic_attention_mask, topic_token_type_ids):
        essay_outputs = self.electra(input_ids=essay_input_ids, attention_mask=essay_attention_mask, token_type_ids=essay_token_type_ids).last_hidden_state
        topic_outputs = self.electra(input_ids=topic_input_ids, attention_mask=topic_attention_mask, token_type_ids=topic_token_type_ids).last_hidden_state
        
        pooled_essay = self.pooler(essay_outputs, essay_attention_mask)
        pooled_topic = self.pooler(topic_outputs, topic_attention_mask)
        
        # Generate the attention-based response using the ResponsePromptAttention layer
        attention_response = self.response_prompt_attention(pooled_essay, pooled_topic)
        
        # Concatenate the pooled essay with the attention response
        concatenated_output = torch.cat([pooled_essay, attention_response], dim=-1)
        
        # Apply dropout to the concatenated output
        dropout_output = self.dropout(concatenated_output)
        
        # Output layer
        return self.out(dropout_output)

