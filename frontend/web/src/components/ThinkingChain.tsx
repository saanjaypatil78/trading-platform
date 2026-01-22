"use client";

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ArrowRight, GitBranch, AlertCircle, CheckCircle2 } from 'lucide-react';

interface Thought {
    thought: string;
    thought_number: number;
    branch_id?: string;
    is_revision?: boolean;
}

interface ThinkingChainProps {
    trace: Thought[];
}

export function ThinkingChain({ trace }: ThinkingChainProps) {
    return (
        <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
                <GitBranch className="h-5 w-5 text-blue-500" />
                AI Reasoning Chain
            </h3>

            <div className="relative border-l-2 border-gray-200 dark:border-gray-800 ml-4 space-y-6 pl-6 py-2">
                {trace.map((step, idx) => (
                    <div key={idx} className="relative">
                        {/* Timeline Node */}
                        <div className={`absolute -left-[33px] top-1 h-4 w-4 rounded-full border-2 border-white dark:border-zinc-950 ${step.branch_id === 'caution_branch' ? 'bg-amber-500' : 'bg-blue-500'
                            }`} />

                        <Card className="border-l-4 border-l-transparent hover:border-l-blue-500 transition-all">
                            <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
                                <div className="flex items-center gap-2 text-sm text-gray-500">
                                    <span className="font-mono">Step {step.thought_number}</span>
                                    {step.branch_id && step.branch_id !== 'main' && (
                                        <Badge variant="secondary" className="text-amber-600 bg-amber-100">
                                            Branch: {step.branch_id}
                                        </Badge>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="py-3 px-4">
                                <p className="text-sm">{step.thought}</p>
                            </CardContent>
                        </Card>
                    </div>
                ))}
            </div>
        </div>
    );
}
