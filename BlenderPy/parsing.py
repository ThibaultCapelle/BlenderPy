# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 20:55:45 2021

@author: Thibault
"""

class Node:
    
    def __init__(self, name='X'):
        self.name

class Token:
    
    def __init__(self, token_type='', content=''):
        self.token_type=token_type
        self.content=content

class Operator:
    
    def __init__(self, left=None, right=None):
        self.left=left
        self.right=right

class Expression:
    
    specials=['(',')','+','-','/','*','^','e','|']
    numbers=['.','0','1','2','3','4','5','6','7','8','9']
    nodes=['x','y','z', 'X', 'Y', 'Z']
    
    def __init__(self, content='', nodes=[], operation=None, tokens=[]):
        self.shader=None
        self.content=content
        self.nodes=nodes
        self.operation=operation
        self.tokens=tokens
        self.lexer()
        self.parenthesis()
        self.parse()
        self.clean_tree()
    
    def lexer(self):
        i=0
        previous_token=None
        while i<len(self.content):
            
            if self.content[i] in Expression.specials:
                if self.content[i]=='-' and previous_token is None:
                    token=Token('number','-1')
                    self.tokens.append(token)
                    token=Token('operator','*')
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i]=='-' and previous_token.content in ['(','^','+','/','*','|']:
                    token=Token('number','-1')
                    self.tokens.append(token)
                    token=Token('operator','*')
                    self.tokens.append(token)
                    previous_token=token
                elif self.content[i] in ['(','e'] and \
                previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                    token=Token('operator',self.content[i])
                    self.tokens.append(token)
                    previous_token=token
                else:
                    token=Token('operator',self.content[i])
                    previous_token=token
                    self.tokens.append(token)
                i+=1
            elif self.content[i] in Expression.numbers:
                if previous_token is not None and previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                j=0
                while self.content[i+j] in Expression.numbers:
                    j+=1
                token=Token('number',self.content[i:i+j])
                self.tokens.append(token)
                previous_token=token
                i=i+j
            elif self.content[i] in Expression.nodes:
                if previous_token is not None and previous_token.content in Expression.numbers:
                    token=Token('operator','*')
                    self.tokens.append(token)
                token=Token('number',self.content[i])
                self.tokens.append(token)
                previous_token=token
                i+=1
            else:
                print("unexpected character")
    
    def parenthesis(self):
        done=False
        while not done:
            ind_start, ind_stop=None, None
            for i,t in enumerate(self.tokens):
                if t.content=='(':
                     ind_start=i
                elif t.content==')':
                     ind_stop=i
                     break
            if ind_start is not None and ind_stop is not None:
                tokens=self.tokens[ind_start+1:ind_stop]
                for i in range(ind_start, ind_stop+1)[::-1]:
                    self.tokens.pop(i)
                node=Expression(tokens=tokens)
                self.tokens.insert(ind_start,node)
            else:
                done=True
                    
    
    def parse(self):
        operation_found=False
        for i,t in enumerate(self.tokens):
            if t.content in ['+','-']:
                operation_found=True
                node_1=Expression(tokens=self.tokens[:i])
                node_2=Expression(tokens=self.tokens[i+1:])
                self.nodes=[node_1, node_2]
                self.operation=t.content
        if not operation_found:
            for i,t in enumerate(self.tokens):
                if t.content in ['*','/']:
                    operation_found=True
                    node_1=Expression(tokens=self.tokens[:i])
                    node_2=Expression(tokens=self.tokens[i+1:])
                    self.nodes=[node_1, node_2]
                    self.operation=t.content
        if not operation_found:
            for i,t in enumerate(self.tokens):
                if t.content in ['^']:
                    operation_found=True
                    node_1=Expression(tokens=self.tokens[:i])
                    node_2=Expression(tokens=self.tokens[i+1:])
                    self.nodes=[node_1, node_2]
                    self.operation=t.content
    
    
    def isleaf(self):
        return len(self.tokens)==1 and not isinstance(self.tokens[0], Expression)
                    
    def get_leaves(self):
        if self.isleaf():
            return [self.tokens[0].content]
        leaves=[]
        if len(self.tokens)==1 and isinstance(self.tokens[0], Expression):
            leaves+=self.tokens[0].get_leaves()
        else:
            for node in self.nodes:
                leaves+=node.get_leaves()
        return leaves
    
    def clean_tree(self):
        for i, node in enumerate(self.nodes):
            if len(node.tokens)==1 and isinstance(node.tokens[0], Expression):
                self.nodes[i]=node.tokens[0]
    
    def get_tree(self):
        if self.isleaf():
            return self.tokens[0].content
        else:
            return dict({self.operation:[node.get_tree() for node in self.nodes]})
        
        

if __name__=='__main__':
    expression=Expression(content='-4e^(-(x^2+y^2)/(0.1)^2)', tokens=[])
    res=expression.get_tree()
    
            
    